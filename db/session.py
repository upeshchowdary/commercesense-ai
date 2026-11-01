"""
session.py — SQLAlchemy 2.0 Engine & Sessionmaker for CommerceSense AI v3.

Provides connection pooling, dialect auto-detection (PostgreSQL vs. SQLite fallback),
and FastAPI dependency injection for transactional database sessions.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_database_url() -> str:
    """Resolves database URL, defaulting to local SQLite database if PostgreSQL is unset."""
    raw_url = os.environ.get("DATABASE_URL")
    if not raw_url:
        sqlite_path = os.environ.get("SQLITE_DB_PATH", "amazon_copilot.db")
        path_obj = Path(sqlite_path)
        full_path = path_obj if path_obj.is_absolute() else (PROJECT_ROOT / path_obj)
        return f"sqlite:///{full_path.as_posix()}"

    # psycopg3 driver prefix normalization for postgresql
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    return raw_url


def create_app_engine(url: str | None = None):
    db_url = url or get_database_url()
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True,
    )


engine = create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def init_db_schema(engine_instance=None) -> None:
    """Idempotently creates all tables defined in Base metadata."""
    target_engine = engine_instance or engine
    Base.metadata.create_all(bind=target_engine)


def get_session() -> Session:
    """Returns a standalone SQLAlchemy Session."""
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed transactional database session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def db_session_scope(engine_instance=None) -> Generator[Session, None, None]:
    """Context manager for non-HTTP background workers and CLI utilities."""
    maker = sessionmaker(autocommit=False, autoflush=False, bind=engine_instance or engine, future=True)
    session = maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
