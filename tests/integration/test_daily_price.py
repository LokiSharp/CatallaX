"""PostgreSQL integration tests for daily_price (Milestone 1.2)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from catallax.db.repositories.daily_price import DailyPriceRepository
from catallax.db.repositories.instrument import InstrumentRepository
from catallax.domain.enums import AssetType, Market

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _make_instrument(
    session: Session,
    *,
    symbol: str,
    market: str,
    exchange: str,
) -> int:
    repo = InstrumentRepository(session)
    row = repo.create(
        symbol=symbol,
        name_cn=symbol,
        market=market,
        exchange=exchange,
        currency="USD" if market == Market.US.value else "CNY",
        asset_type=AssetType.EQUITY.value,
    )
    session.flush()
    return row.id


def test_daily_price_insert_and_get(db_session: Session) -> None:
    instrument_id = _make_instrument(
        db_session, symbol="AAPL", market=Market.US.value, exchange="NASDAQ"
    )
    prices = DailyPriceRepository(db_session)
    trade_date = date(2024, 1, 2)
    row = prices.create(
        instrument_id=instrument_id,
        trade_date=trade_date,
        open_=Decimal("10.0"),
        high=Decimal("11.0"),
        low=Decimal("9.5"),
        close=Decimal("10.5"),
        volume=Decimal(1000),
        amount=Decimal(10500),
        source="manual",
    )
    db_session.flush()

    loaded = prices.get(instrument_id=instrument_id, trade_date=trade_date)
    assert loaded is not None
    assert loaded.instrument_id == row.instrument_id
    assert loaded.close == Decimal("10.5")
    assert loaded.source == "manual"


def test_daily_price_natural_key_unique(db_session: Session) -> None:
    instrument_id = _make_instrument(
        db_session, symbol="AAPL", market=Market.US.value, exchange="NASDAQ"
    )
    prices = DailyPriceRepository(db_session)
    trade_date = date(2024, 1, 2)
    prices.create(
        instrument_id=instrument_id,
        trade_date=trade_date,
        open_=Decimal("10.0"),
        high=Decimal("11.0"),
        low=Decimal("9.5"),
        close=Decimal("10.5"),
        volume=Decimal(1000),
        source="manual",
    )
    db_session.flush()

    def _duplicate() -> None:
        prices.create(
            instrument_id=instrument_id,
            trade_date=trade_date,
            open_=Decimal("10.0"),
            high=Decimal("11.0"),
            low=Decimal("9.5"),
            close=Decimal("99.0"),
            volume=Decimal(1000),
            source="manual",
        )
        db_session.flush()

    with db_session.begin_nested(), pytest.raises(IntegrityError):
        _duplicate()


def test_daily_price_upsert_is_idempotent(db_session: Session) -> None:
    instrument_id = _make_instrument(
        db_session, symbol="600519", market=Market.CN.value, exchange="SSE"
    )
    prices = DailyPriceRepository(db_session)
    trade_date = date(2024, 3, 1)

    first = prices.upsert(
        instrument_id=instrument_id,
        trade_date=trade_date,
        open_=Decimal(1600),
        high=Decimal(1620),
        low=Decimal(1590),
        close=Decimal(1610),
        volume=Decimal(10000),
        amount=Decimal(16100000),
        source="akshare",
    )
    second = prices.upsert(
        instrument_id=instrument_id,
        trade_date=trade_date,
        open_=Decimal(1600),
        high=Decimal(1630),
        low=Decimal(1585),
        close=Decimal(1625),
        volume=Decimal(12000),
        amount=Decimal(19400000),
        source="akshare",
    )
    db_session.flush()

    assert first.instrument_id == second.instrument_id
    assert first.trade_date == second.trade_date
    assert second.close == Decimal(1625)
    assert second.volume == Decimal(12000)
    history = prices.list_by_instrument(instrument_id)
    assert len(history) == 1


def test_list_by_instrument_and_by_market_date(db_session: Session) -> None:
    us_id = _make_instrument(
        db_session, symbol="MSFT", market=Market.US.value, exchange="NASDAQ"
    )
    cn_id = _make_instrument(
        db_session, symbol="000001", market=Market.CN.value, exchange="SZSE"
    )
    prices = DailyPriceRepository(db_session)
    d1 = date(2024, 6, 3)
    d2 = date(2024, 6, 4)

    prices.upsert(
        instrument_id=us_id,
        trade_date=d1,
        open_=Decimal(400),
        high=Decimal(405),
        low=Decimal(398),
        close=Decimal(402),
        volume=Decimal(1000000),
        source="manual",
    )
    prices.upsert(
        instrument_id=us_id,
        trade_date=d2,
        open_=Decimal(402),
        high=Decimal(410),
        low=Decimal(401),
        close=Decimal(408),
        volume=Decimal(1100000),
        source="manual",
    )
    prices.upsert(
        instrument_id=cn_id,
        trade_date=d1,
        open_=Decimal(10),
        high=Decimal("10.5"),
        low=Decimal("9.8"),
        close=Decimal("10.2"),
        volume=Decimal(2000000),
        source="manual",
    )
    db_session.flush()

    us_history = prices.list_by_instrument(us_id)
    assert [b.trade_date for b in us_history] == [d1, d2]

    us_range = prices.list_by_instrument(us_id, start=d2, end=d2)
    assert len(us_range) == 1
    assert us_range[0].close == Decimal(408)

    day_all = prices.list_by_trade_date(d1)
    assert {b.instrument_id for b in day_all} == {us_id, cn_id}

    day_us = prices.list_by_market_and_date(market=Market.US.value, trade_date=d1)
    assert len(day_us) == 1
    assert day_us[0].instrument_id == us_id

    day_cn = prices.list_by_market_and_date(market=Market.CN.value, trade_date=d1)
    assert len(day_cn) == 1
    assert day_cn[0].instrument_id == cn_id
