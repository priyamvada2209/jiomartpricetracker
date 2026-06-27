from __future__ import annotations

import asyncio
import os


def send_message(text: str, chat_id: int) -> None:
    async def _send() -> None:
        try:
            from telegram import Bot
        except ImportError as exc:  # pragma: no cover - environment specific
            raise RuntimeError(
                "python-telegram-bot is required. Install dependencies from requirements.txt."
            ) from exc

        bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN is required to send Telegram messages.")

        await Bot(token=bot_token).send_message(chat_id=chat_id, text=text)

    asyncio.run(_send())
