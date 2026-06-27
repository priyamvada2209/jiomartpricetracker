"""
Database repository helpers for prices and Telegram users.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .fetcher import ProductPrice
from .models import PriceHistory, TelegramUser


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def upsert_telegram_user(
    session: Session,
    *,
    telegram_chat_id: int,
    telegram_user_id: int,
    username: str | None,
    first_name: str | None,
    notifications_enabled: bool = True,
) -> TelegramUser:
    user = session.query(TelegramUser).filter_by(telegram_chat_id=telegram_chat_id).one_or_none()
    now = _utcnow()

    if user is None:
        user = TelegramUser(
            telegram_chat_id=telegram_chat_id,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            created_at=now,
            last_seen=now,
            notifications_enabled=notifications_enabled,
        )
        session.add(user)
        return user

    user.telegram_user_id = telegram_user_id
    user.username = username
    user.first_name = first_name
    user.last_seen = now
    user.notifications_enabled = notifications_enabled
    return user


def set_notifications_enabled(session: Session, telegram_chat_id: int, enabled: bool) -> TelegramUser | None:
    user = session.query(TelegramUser).filter_by(telegram_chat_id=telegram_chat_id).one_or_none()
    if user is None:
        return None

    user.notifications_enabled = enabled
    user.last_seen = _utcnow()
    return user


def list_active_telegram_users(session: Session) -> list[TelegramUser]:
    return (
        session.query(TelegramUser)
        .filter(TelegramUser.notifications_enabled.is_(True))
        .order_by(TelegramUser.id.asc())
        .all()
    )


def store_price_history(session: Session, prices: list[ProductPrice]) -> list[PriceHistory]:
    records: list[PriceHistory] = []
    now = _utcnow()
    for price in prices:
        record = PriceHistory(
            product_slug=price.slug,
            product_name=price.product_name,
            price=price.effective_price if price.is_serviceable else None,
            fetched_at=now,
        )
        session.add(record)
        records.append(record)
    return records


def get_latest_price_history(session: Session) -> list[PriceHistory]:
    ordered_records = (
        session.query(PriceHistory)
        .order_by(PriceHistory.product_slug.asc(), PriceHistory.fetched_at.desc(), PriceHistory.id.desc())
        .all()
    )
    latest_by_slug: dict[str, PriceHistory] = {}
    for record in ordered_records:
        latest_by_slug.setdefault(record.product_slug, record)
    return list(latest_by_slug.values())