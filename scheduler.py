from __future__ import annotations


def run_price_tracker_job() -> None:
    from jiomart_price_tracker.jobs import run_price_refresh_once

    run_price_refresh_once()


def start_scheduler():
    from jiomart_price_tracker.scheduler import DailyPriceScheduler
    from jiomart_price_tracker.web import get_telegram_runtime

    scheduler = DailyPriceScheduler(get_telegram_runtime())
    scheduler.start()
    return scheduler
