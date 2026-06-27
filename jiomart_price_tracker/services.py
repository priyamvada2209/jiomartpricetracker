"""
Application services for price fetching and persistence.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from .database import get_db
from .fetcher import ProductPrice, fetch_all_registered_products
from .repositories import get_latest_price_history, store_price_history
from .summary import format_latest_stored_summary, format_price_summary


class PriceService:
    def __init__(
        self,
        session_factory: Callable[[], AbstractContextManager[Session]] = get_db,
        product_fetcher: Callable[[], list[ProductPrice]] = fetch_all_registered_products,
    ) -> None:
        self._session_factory = session_factory
        self._product_fetcher = product_fetcher

    def fetch_and_store_prices(self) -> list[ProductPrice]:
        prices = self._product_fetcher()
        with self._session_factory() as session:
            store_price_history(session, prices)
        return prices

    def fetch_store_and_build_summary(self) -> str:
        prices = self.fetch_and_store_prices()
        return format_price_summary(prices)

    def latest_stored_summary(self) -> str:
        with self._session_factory() as session:
            latest_prices = get_latest_price_history(session)
        return format_latest_stored_summary(latest_prices)

