"""
Models module for the JioMart Price Tracker.

Defines the SQLAlchemy ORM models representing the database schema.
"""

from datetime import datetime
from typing import Any
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base

# Create declarative base for ORM classes
Base: Any = declarative_base()

class PriceHistory(Base):
    """
    ORM Model representing the price_history database table.

    Attributes:
        id (int): Primary key.
        product_slug (str): Slug identifier of the product.
        product_name (str): Decoded name of the product.
        price (float): Fetched selling price (effective price). Nullable if not serviceable.
        fetched_at (datetime): Timestamp when the price was fetched.
    """
    __tablename__ = "price_history"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    product_slug: str = Column(String(255), nullable=False)
    product_name: str = Column(String(255), nullable=True)
    price: float = Column(Float, nullable=True)
    fetched_at: datetime = Column(DateTime, nullable=False, default=datetime.now)
