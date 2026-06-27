"""
ORM models for the JioMart Price Tracker bot.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, BigInteger, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_slug = Column(String(255), nullable=False, index=True)
    product_name = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)


class TelegramUser(Base):
    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_seen = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)
    notifications_enabled = Column(Boolean, nullable=False, default=True)