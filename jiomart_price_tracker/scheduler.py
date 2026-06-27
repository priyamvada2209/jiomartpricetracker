"""
Background scheduler for the daily JioMart summary.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from .telegram_runtime import TelegramBotRuntime

logger = logging.getLogger(__name__)


class DailyPriceScheduler:
    def __init__(self, runtime: TelegramBotRuntime, hour: int = 6, minute: int = 0) -> None:
        self.runtime = runtime
        self.hour = hour
        self.minute = minute
        self._scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def start(self) -> None:
        self._scheduler.add_job(
            self._run_daily_job,
            "cron",
            hour=self.hour,
            minute=self.minute,
            id="jiomart_daily_fetch_job",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
        )
        self._scheduler.start()
        logger.info("APScheduler daily job registered for %02d:%02d.", self.hour, self.minute)

    def _run_daily_job(self) -> None:
        logger.info("Executing scheduled JioMart summary job...")
        try:
            future = self.runtime._submit(self.runtime.run_daily_summary_cycle())
            future.result(timeout=900)
            logger.info("Scheduled JioMart summary job finished successfully.")
        except Exception:
            logger.exception("Scheduled JioMart summary job failed.")

