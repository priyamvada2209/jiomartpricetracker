"""
Database management module for the JioMart Price Tracker.

Handles creation of the SQLAlchemy engine, session maker, and
database initialization.
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import config
from models import Base

import os

# Configure the SQLite / SQL database engine.
# Resolve relative sqlite database paths to the project directory.
db_url = config.database_url
if db_url.startswith("sqlite:///"):
    db_file = db_url[len("sqlite:///"):]
    if not os.path.isabs(db_file):
        project_dir = os.path.dirname(os.path.abspath(__file__))
        db_file = os.path.abspath(os.path.join(project_dir, db_file))
        db_url = f"sqlite:///{db_file}"

# If SQLite is used, check_same_thread is set to False for scheduler multi-threading safety.
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args)

# Create session factory binded to engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db() -> None:
    """
    Initializes the database and creates all tables defined in models.py if they do not exist.
    """
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Provides a transactional database session context.

    Automatically handles commits, rollbacks on failure, and cleanup on exit.

    Yields:
        Session: Active SQLAlchemy database session.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
