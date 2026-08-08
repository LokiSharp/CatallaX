"""Shared pytest fixtures."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from catallax.config import settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session


def _replace_database_name(url: str, database: str) -> str:
    """Swap the database path segment of a SQLAlchemy URL."""
    parsed = urlparse(url)
    new_path = f"/{database}"
    return urlunparse(parsed._replace(path=new_path))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """URL for the isolated integration database."""
    explicit = os.environ.get("CATALLAX_TEST_DATABASE_URL")
    if explicit:
        return explicit
    return _replace_database_name(settings.database_url, "catallax_test")


@pytest.fixture(scope="session")
def pg_engine(test_database_url: str) -> Generator[Engine]:
    """Yield an engine for catallax_test after applying migrations.

    Skips the integration suite if PostgreSQL is unreachable.
    Create the DB first with: ``devbox run db-init``.
    """
    engine = create_engine(test_database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — offline unit runs should skip
        engine.dispose()
        pytest.skip(f"PostgreSQL test database not available: {exc}")

    previous_url = os.environ.get("CATALLAX_DATABASE_URL")
    os.environ["CATALLAX_DATABASE_URL"] = test_database_url
    try:
        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
    finally:
        if previous_url is None:
            os.environ.pop("CATALLAX_DATABASE_URL", None)
        else:
            os.environ["CATALLAX_DATABASE_URL"] = previous_url

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(pg_engine: Engine) -> Generator[Session]:
    """Session wrapped in a transaction that is rolled back after each test."""
    connection = pg_engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
