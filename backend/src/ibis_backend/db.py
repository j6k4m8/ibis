"""Database setup and session management."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ibis_backend.config import get_settings


class Base(DeclarativeBase):
    """Base class for ORM models."""



def build_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the given database URL.

    Args:
        database_url: Database connection string.

    Returns:
        Engine: SQLAlchemy engine instance.
    """

    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            return create_engine(
                database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                future=True,
            )
        return create_engine(database_url, connect_args=connect_args, future=True)
    return create_engine(database_url, pool_pre_ping=True, future=True)


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Initialize database tables or apply migrations."""

    import ibis_backend.models  # noqa: F401

    database_url = get_settings().database_url
    if database_url in {"sqlite://", "sqlite:///:memory:"}:
        Base.metadata.create_all(bind=engine)
        return

    base_dir = Path(__file__).resolve().parents[3]
    alembic_ini = base_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")


def get_db() -> Generator[Session, None, None]:
    """Provide a database session.

    Yields:
        Session: SQLAlchemy session.
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
