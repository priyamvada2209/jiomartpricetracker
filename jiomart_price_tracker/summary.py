"""
Human-readable summary formatting helpers.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from .fetcher import ProductPrice
from .models import PriceHistory


def _format_price(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def format_price_summary(prices: Sequence[ProductPrice], *, title: str = "JioMart Daily Prices") -> str:
    if not prices:
        return f"{title}\n\nNo prices available."

    lines = [title]
    for price in prices:
        lines.append(price.product_name)
        if price.is_serviceable:
            lines.append(f"Rs {_format_price(price.effective_price)} (MRP Rs {_format_price(price.marked_price)})")
        else:
            lines.append("Not Serviceable")
    return "\n".join(lines)


def format_latest_stored_summary(
    prices: Sequence[PriceHistory],
    *,
    title: str = "Latest stored JioMart prices",
) -> str:
    if not prices:
        return f"{title}\n\nNo stored prices found yet. Send /today to fetch the latest JioMart prices."

    lines = [title]
    for price in prices:
        lines.append(price.product_name or price.product_slug)
        if price.price is None:
            lines.append("Not Serviceable")
        else:
            lines.append(f"Rs {_format_price(price.price)}")
    return "\n".join(lines)


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "unknown time"
    return value.strftime("%Y-%m-%d %H:%M:%S UTC")
