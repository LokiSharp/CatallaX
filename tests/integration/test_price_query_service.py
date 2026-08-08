"""Integration tests for PriceQueryService (PostgreSQL, no provider I/O)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from catallax.db.repositories.daily_price import DailyPriceRepository
from catallax.db.repositories.instrument import InstrumentRepository
from catallax.domain.enums import Market
from catallax.services.prices import PriceQueryService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _seed_with_bars(session: Session) -> int:
    inst = InstrumentRepository(session).create(
        symbol="AAPL",
        market=Market.US.value,
        exchange="NASDAQ",
        name_cn="苹果",
        currency="USD",
    )
    session.flush()
    prices = DailyPriceRepository(session)
    for d, close in (
        (date(2024, 1, 2), Decimal(100)),
        (date(2024, 1, 3), Decimal(101)),
        (date(2024, 1, 4), Decimal(102)),
    ):
        prices.create(
            instrument_id=inst.id,
            trade_date=d,
            open_=close,
            high=close,
            low=close,
            close=close,
            volume=Decimal(1000),
            amount=Decimal(100000),
            source="longbridge:forward",
        )
    session.flush()
    return inst.id


def test_get_prices_by_instrument_id_ordered(db_session: Session) -> None:
    instrument_id = _seed_with_bars(db_session)
    svc = PriceQueryService(db_session)
    bars = svc.get_prices(
        instrument_id=instrument_id,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 4),
    )
    assert [b.trade_date for b in bars] == [
        date(2024, 1, 2),
        date(2024, 1, 3),
        date(2024, 1, 4),
    ]
    assert bars[0].close == Decimal(100)
    assert bars[-1].close == Decimal(102)
    assert bars[0].source == "longbridge:forward"
    assert bars[0].instrument_id == instrument_id


def test_get_prices_date_range_filter(db_session: Session) -> None:
    instrument_id = _seed_with_bars(db_session)
    svc = PriceQueryService(db_session)
    bars = svc.get_prices(
        instrument_id=instrument_id,
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 3),
    )
    assert len(bars) == 1
    assert bars[0].trade_date == date(2024, 1, 3)


def test_get_prices_by_symbol(db_session: Session) -> None:
    _seed_with_bars(db_session)
    svc = PriceQueryService(db_session)
    bars = svc.get_prices_by_symbol(
        market="us",
        symbol="aapl",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 4),
    )
    assert len(bars) == 3


def test_get_prices_by_symbol_missing_raises(db_session: Session) -> None:
    svc = PriceQueryService(db_session)
    with pytest.raises(LookupError, match="instrument not found"):
        svc.get_prices_by_symbol(
            market=Market.US.value,
            symbol="NOSUCH",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )
