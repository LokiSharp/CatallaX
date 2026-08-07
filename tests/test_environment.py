"""Environment / wiring smoke tests (no live PostgreSQL required)."""

from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

import catallax
from catallax.config import settings
from catallax.db.base import Base
from catallax.db.session import get_engine


def test_package_importable() -> None:
    assert catallax.__version__


def test_settings_load() -> None:
    assert settings.database_url
    assert "postgresql" in settings.database_url
    assert settings.env


def test_sqlalchemy_base_exists() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_engine_can_be_created() -> None:
    engine = get_engine()
    assert isinstance(engine, Engine)
    assert engine.url.drivername.startswith("postgresql")
