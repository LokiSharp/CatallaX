"""SQLAlchemy engine and session factory."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from catallax.config import settings

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.engine import Engine
    from sqlalchemy.orm import Session


@dataclass
class _RuntimeState:
    """Mutable module state without `global` rebinding."""

    engine: Engine | None = None
    session_factory: sessionmaker[Session] | None = field(default=None)


_state = _RuntimeState()


def get_engine(url: str | None = None) -> Engine:
    """Create (or reuse) the SQLAlchemy engine for the configured database URL."""
    if url is not None:
        return create_engine(url, pool_pre_ping=True)
    if _state.engine is None:
        _state.engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _state.engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a session factory bound to the given (or default) engine."""
    if engine is not None:
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)
    if _state.session_factory is None:
        _state.session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
        )
    return _state.session_factory


@contextmanager
def session_scope() -> Generator[Session]:
    """Provide a transactional scope around a series of operations."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
