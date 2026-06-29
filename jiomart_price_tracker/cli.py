"""
Command-line helpers for one-off execution.
"""

from __future__ import annotations

import asyncio

from .web import get_telegram_runtime


def run_daily_job_once() -> None:
    runtime = get_telegram_runtime()
    asyncio.run(runtime.run_daily_summary_cycle())


if __name__ == "__main__":
    run_daily_job_once()
