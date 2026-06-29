"""
Flask application factory for the Telegram webhook and health checks.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from flask import Flask, jsonify, request

from . import config
from .database import init_db
from .scheduler import DailyPriceScheduler
from .services import PriceService
from .telegram_runtime import TelegramBotRuntime


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(config.log_file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


@lru_cache(maxsize=1)
def get_price_service() -> PriceService:
    return PriceService()


@lru_cache(maxsize=1)
def get_telegram_runtime() -> TelegramBotRuntime:
    runtime = TelegramBotRuntime(get_price_service())
    runtime.start()
    return runtime


@lru_cache(maxsize=1)
def get_scheduler() -> DailyPriceScheduler:
    scheduler = DailyPriceScheduler(get_telegram_runtime())
    scheduler.start()
    return scheduler


def create_app() -> Flask:
    configure_logging()
    init_db()
    runtime = get_telegram_runtime()
    scheduler = get_scheduler()

    app = Flask(__name__)
    app.config["TELEGRAM_RUNTIME"] = runtime
    app.config["DAILY_SCHEDULER"] = scheduler
    app.config["JSON_SORT_KEYS"] = False

    @app.get("/health")
    def health() -> tuple[dict[str, str], int]:
        return {"status": "ok"}, 200

    @app.post("/webhook")
    def webhook() -> tuple[object, int]:
        payload = request.get_json(silent=True)
        logger = logging.getLogger(__name__)
        if not isinstance(payload, dict):
            logger.warning("Rejected webhook request with invalid payload type: %s", type(payload).__name__)
            return jsonify({"ok": False, "error": "Invalid Telegram update payload"}), 400

        logger.info(
            "Webhook request accepted: update_id=%s keys=%s",
            payload.get("update_id"),
            sorted(payload.keys()),
        )

        try:
            runtime.process_webhook_payload(payload)
        except Exception:
            logger.exception("Webhook processing failed.")
            return jsonify({"ok": False, "error": "Failed to process update"}), 500

        return jsonify({"ok": True}), 200

    return app
