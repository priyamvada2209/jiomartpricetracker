"""
Telegram bot runtime built on python-telegram-bot v22+.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy.orm import Session

from . import config
from .database import get_db
from .repositories import list_active_telegram_users, set_notifications_enabled, upsert_telegram_user
from .services import PriceService

logger = logging.getLogger(__name__)

START_MESSAGE = (
    "Welcome to JioMart Price Tracker.\n\n"
    "You'll receive a daily price summary every morning.\n\n"
    "Commands:\n\n"
    "/today\n"
    "/prices\n"
    "/help\n"
    "/stop\n"
    "/start"
)

HELP_MESSAGE = (
    "Available commands:\n\n"
    "/start - enable notifications\n"
    "/today - fetch today's prices now\n"
    "/prices - show the latest stored prices\n"
    "/help - show this help text\n"
    "/stop - disable notifications"
)

STOP_MESSAGE = "Notifications disabled. Send /start to enable them again."
TODAY_ERROR_MESSAGE = "Sorry, I couldn't fetch today's prices right now. Please try again later."
PRICES_ERROR_MESSAGE = "Sorry, I couldn't read the latest stored prices right now. Please try again later."


def _load_telegram_modules() -> dict[str, Any]:
    try:
        from telegram import Update
        from telegram.error import Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut
        from telegram.ext import Application, CommandHandler
    except ImportError as exc:  # pragma: no cover - environment specific
        raise RuntimeError(
            "python-telegram-bot is required. Install dependencies from requirements.txt."
        ) from exc

    return {
        "Update": Update,
        "Forbidden": Forbidden,
        "NetworkError": NetworkError,
        "RetryAfter": RetryAfter,
        "TelegramError": TelegramError,
        "TimedOut": TimedOut,
        "Application": Application,
        "CommandHandler": CommandHandler,
    }


class TelegramBotRuntime:
    def __init__(
        self,
        price_service: PriceService,
        session_factory: Callable[[], AbstractContextManager[Session]] = get_db,
    ) -> None:
        if not config.bot_token:
            raise ValueError("BOT_TOKEN is required to start the Telegram runtime.")
        if not config.webhook_url:
            raise ValueError("WEBHOOK_URL is required to start the Telegram runtime.")

        modules = _load_telegram_modules()
        self._Update = modules["Update"]
        self._Forbidden = modules["Forbidden"]
        self._NetworkError = modules["NetworkError"]
        self._RetryAfter = modules["RetryAfter"]
        self._TelegramError = modules["TelegramError"]
        self._TimedOut = modules["TimedOut"]
        self._Application = modules["Application"]
        self._CommandHandler = modules["CommandHandler"]

        self.price_service = price_service
        self._session_factory = session_factory
        self.application = self._Application.builder().token(config.bot_token).build()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = False
        self._register_handlers()
        self.application.add_error_handler(self._handle_telegram_error)

    def _register_handlers(self) -> None:
        self.application.add_handler(self._CommandHandler("start", self.handle_start))
        self.application.add_handler(self._CommandHandler("today", self.handle_today))
        self.application.add_handler(self._CommandHandler("prices", self.handle_prices))
        self.application.add_handler(self._CommandHandler("help", self.handle_help))
        self.application.add_handler(self._CommandHandler("stop", self.handle_stop))

    def start(self) -> None:
        if self._started:
            return

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, name="telegram-runtime", daemon=False)
        self._thread.start()
        self._submit(self._initialize()).result(timeout=60)
        self._started = True
        logger.info("Telegram runtime initialized and webhook configured.")

    def _run_loop(self) -> None:
        assert self._loop is not None
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _submit(self, coroutine: Any):
        if self._loop is None:
            raise RuntimeError("Telegram runtime has not been started.")
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    def submit_webhook_payload(self, payload: dict[str, Any]):
        logger.info(
            "Webhook payload received: update_id=%s keys=%s",
            payload.get("update_id"),
            sorted(payload.keys()),
        )
        future = self._submit(self._process_payload(payload))
        future.add_done_callback(self._log_background_exception)
        return future

    def process_webhook_payload(self, payload: dict[str, Any]):
        return self.submit_webhook_payload(payload)

    def _log_background_exception(self, future: Any) -> None:
        try:
            future.result()
        except Exception:
            logger.exception("Webhook update processing failed.")

    async def _handle_telegram_error(self, update: Any, context: Any) -> None:
        logger.exception(
            "Telegram handler error for update_id=%s error=%s",
            getattr(update, "update_id", None),
            getattr(context, "error", None),
        )

    async def _initialize(self) -> None:
        logger.info("Initializing Telegram application and setting webhook %s", config.webhook_url)
        await self.application.initialize()
        await self.application.start()
        await self.application.bot.set_webhook(url=config.webhook_url, drop_pending_updates=True)

    async def _process_payload(self, payload: dict[str, Any]) -> None:
        update = self._Update.de_json(payload, self.application.bot)
        logger.info(
            "Processing update_id=%s chat_id=%s user_id=%s",
            getattr(update, "update_id", None),
            getattr(getattr(update, "effective_chat", None), "id", None),
            getattr(getattr(update, "effective_user", None), "id", None),
        )
        await self.application.process_update(update)

    async def _send_message_with_retry(self, chat_id: int, text: str) -> None:
        delay_seconds = 1.0
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                await self.application.bot.send_message(chat_id=chat_id, text=text)
                logger.info("Sent Telegram message to chat_id=%s", chat_id)
                return
            except self._RetryAfter as exc:
                wait_seconds = max(float(exc.retry_after), 1.0)
                logger.warning("Telegram rate limit hit for chat %s, retrying in %s seconds", chat_id, wait_seconds)
                await asyncio.sleep(wait_seconds)
            except (self._NetworkError, self._TimedOut) as exc:
                logger.warning("Transient Telegram error for chat %s on attempt %s: %s", chat_id, attempt, exc)
                if attempt == max_attempts:
                    raise
                await asyncio.sleep(delay_seconds)
                delay_seconds *= 2
            except self._Forbidden:
                logger.warning("Telegram bot is forbidden from sending to chat %s.", chat_id)
                return

    async def broadcast_summary(self, summary: str) -> None:
        users = await asyncio.to_thread(self._list_active_users)
        logger.info("Broadcasting summary to %s active Telegram users.", len(users))
        for user in users:
            try:
                await self._send_message_with_retry(user.telegram_chat_id, summary)
            except self._TelegramError as exc:
                logger.error("Failed to send summary to chat %s: %s", user.telegram_chat_id, exc)

    def _list_active_users(self):
        with self._session_factory() as session:
            return list_active_telegram_users(session)

    def _upsert_user(self, chat_id: int, user_id: int, username: str | None, first_name: str | None) -> None:
        with self._session_factory() as session:
            upsert_telegram_user(
                session,
                telegram_chat_id=chat_id,
                telegram_user_id=user_id,
                username=username,
                first_name=first_name,
                notifications_enabled=True,
            )

    def _disable_notifications(self, chat_id: int) -> bool:
        with self._session_factory() as session:
            user = set_notifications_enabled(session, chat_id, False)
            return user is not None

    async def handle_start(self, update: Any, context: Any) -> None:
        chat = update.effective_chat
        user = update.effective_user
        if chat is None or user is None or update.message is None:
            logger.warning("/start received without chat or user context.")
            return

        await asyncio.to_thread(
            self._upsert_user,
            chat.id,
            user.id,
            user.username,
            user.first_name,
        )
        logger.info("Registered/updated Telegram user chat_id=%s user_id=%s", chat.id, user.id)
        await update.message.reply_text(START_MESSAGE)

    async def handle_today(self, update: Any, context: Any) -> None:
        if update.message is None:
            logger.warning("/today received without message context.")
            return

        try:
            summary = await asyncio.to_thread(self.price_service.fetch_store_and_build_summary)
        except Exception:
            logger.exception("Failed to fetch today's prices.")
            await update.message.reply_text(TODAY_ERROR_MESSAGE)
            return

        logger.info("Sending fresh price summary to chat_id=%s", update.effective_chat.id if update.effective_chat else None)
        await update.message.reply_text(summary)

    async def handle_prices(self, update: Any, context: Any) -> None:
        if update.message is None:
            logger.warning("/prices received without message context.")
            return

        try:
            summary = await asyncio.to_thread(self.price_service.latest_stored_summary)
        except Exception:
            logger.exception("Failed to read latest stored prices.")
            await update.message.reply_text(PRICES_ERROR_MESSAGE)
            return

        logger.info("Sending stored price summary to chat_id=%s", update.effective_chat.id if update.effective_chat else None)
        await update.message.reply_text(summary)

    async def handle_help(self, update: Any, context: Any) -> None:
        if update.message is None:
            logger.warning("/help received without message context.")
            return

        logger.info("Help command requested for chat_id=%s", update.effective_chat.id if update.effective_chat else None)
        await update.message.reply_text(HELP_MESSAGE)

    async def handle_stop(self, update: Any, context: Any) -> None:
        chat = update.effective_chat
        if chat is None or update.message is None:
            logger.warning("/stop received without chat or message context.")
            return

        await asyncio.to_thread(self._disable_notifications, chat.id)
        logger.info("Disabled notifications for chat_id=%s", chat.id)
        await update.message.reply_text(STOP_MESSAGE)

    async def run_daily_summary_cycle(self) -> None:
        logger.info("Starting daily summary cycle.")
        summary = await asyncio.to_thread(self.price_service.fetch_store_and_build_summary)
        await self.broadcast_summary(summary)
        logger.info("Finished daily summary cycle.")
