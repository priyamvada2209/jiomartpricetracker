"""
One-off jobs for CI and manual refreshes.
"""

from __future__ import annotations

import logging

from .services import PriceService

logger = logging.getLogger(__name__)


def run_price_refresh_once() -> str:
    price_service = PriceService()
    summary = price_service.fetch_store_and_build_summary()
    logger.info("Completed one-off price refresh job.")
    return summary


if __name__ == "__main__":
    print(run_price_refresh_once())
