"""
Database helpers for SQLAlchemy sessions and schema creation.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from . import config
from .models import Base


def _normalize_database_url(database_url: str) -> str:
    if not database_url.startswith("sqlite:///"):
        return database_url

    sqlite_path = database_url[len("sqlite:///") :]
    if not sqlite_path or sqlite_path == ":memory:":
        return database_url

    if os.path.isabs(sqlite_path):
        return database_url

    resolved_path = Path(config.PROJECT_ROOT, sqlite_path).resolve()
    return f"sqlite:///{resolved_path}"


# def _build_engine(database_url: str):
#     if database_url in {"sqlite://", "sqlite:///:memory:"}:
#         return create_engine(
#             database_url,
#             connect_args={"check_same_thread": False},
#             poolclass=StaticPool,
#             future=True,
#         )

#     connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
#     return create_engine(database_url, connect_args=connect_args, future=True)



def _build_engine(database_url: str):
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )

    connect_args = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    elif database_url.startswith("mysql+pymysql"):
        # Required for Aiven MySQL
        connect_args["ssl"] = {}

    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=3600,
        future=True,
    )

database_url = _normalize_database_url(config.database_url)
engine = _build_engine(database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
