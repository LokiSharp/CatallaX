"""PostgreSQL integration tests for daily price sync + history ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from catallax.db.repositories.daily_price import DailyPriceRepository
from catallax.db.repositories.history_symbol import (
    ProviderHistorySymbolRepository,
    utc_year_month,
)
from catallax.db.repositories.instrument import InstrumentRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.domain.enums import Market, SyncEntity, SyncStatus
from catallax.pipeline.sync_daily_prices import sync_daily_prices
from catallax.providers.base import ProviderDailyBar
from catallax.providers.longbridge.bars import DAILY_BAR_SOURCE

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


class _FakePriceProvider:
    def __init__(self, bars_by_symbol: dict[str, list[ProviderDailyBar]]) -> None:
        self._bars = bars_by_symbol
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "fake"

    def get_daily_bars(
        self,
        *,
        provider_symbol: str,
        start: date,
        end: date,
    ) -> list[ProviderDailyBar]:
        _ = start, end
        self.calls.append(provider_symbol)
        return list(self._bars.get(provider_symbol, []))


def _seed_mapped_instrument(
    session: Session,
    *,
    symbol: str,
    market: str,
    provider_symbol: str,
    provider: str = "fake",
) -> int:
    inst = InstrumentRepository(session).create(
        symbol=symbol,
        market=market,
        exchange="NASDAQ" if market == Market.US.value else "SSE",
        name_cn=symbol,
        currency="USD" if market == Market.US.value else "CNY",
    )
    session.flush()
    InstrumentSymbolMapRepository(session).create(
        instrument_id=inst.id,
        provider=provider,
        provider_symbol=provider_symbol,
        provider_exchange="",
        is_active=True,
    )
    session.flush()
    return inst.id


def test_sync_daily_prices_upserts_and_records_history(db_session: Session) -> None:
    instrument_id = _seed_mapped_instrument(
        db_session,
        symbol="AAPL",
        market=Market.US.value,
        provider_symbol="AAPL.US",
    )
    bar = ProviderDailyBar(
        provider_symbol="AAPL.US",
        trade_date=date(2024, 1, 2),
        open=Decimal(100),
        high=Decimal(110),
        low=Decimal(99),
        close=Decimal(105),
        volume=Decimal(1000),
        amount=Decimal(105000),
        source=DAILY_BAR_SOURCE,
    )
    provider = _FakePriceProvider({"AAPL.US": [bar]})

    first = sync_daily_prices(
        provider=provider,
        start=date(2024, 1, 1),
        end=date(2024, 1, 5),
        markets=["US"],
        symbols=["AAPL"],
        session=db_session,
        throttle_seconds=0.0,
    )
    second = sync_daily_prices(
        provider=provider,
        start=date(2024, 1, 1),
        end=date(2024, 1, 5),
        markets=["US"],
        symbols=["AAPL"],
        session=db_session,
        throttle_seconds=0.0,
    )
    db_session.flush()

    assert first == 1
    assert second == 1
    prices = DailyPriceRepository(db_session).list_by_instrument(instrument_id)
    assert len(prices) == 1
    assert prices[0].close == Decimal(105)
    assert prices[0].source == DAILY_BAR_SOURCE

    ym = utc_year_month()
    history = ProviderHistorySymbolRepository(db_session)
    rows = history.list_by_month(provider="fake", year_month=ym)
    assert len(rows) == 1
    assert rows[0].provider_symbol == "AAPL.US"
    assert rows[0].query_count == 2
    assert history.count_by_month(provider="fake", year_month=ym) == 1

    log = DataSyncLogRepository(db_session).get_latest(
        provider="fake",
        entity=SyncEntity.DAILY_PRICES.value,
    )
    assert log is not None
    assert log.status == SyncStatus.SUCCESS.value
    assert log.records_written == 1


def test_max_new_symbols_limits_first_time_queries(db_session: Session) -> None:
    _seed_mapped_instrument(
        db_session,
        symbol="AAPL",
        market=Market.US.value,
        provider_symbol="AAPL.US",
    )
    _seed_mapped_instrument(
        db_session,
        symbol="MSFT",
        market=Market.US.value,
        provider_symbol="MSFT.US",
    )
    provider = _FakePriceProvider(
        {
            "AAPL.US": [],
            "MSFT.US": [],
        },
    )
    sync_daily_prices(
        provider=provider,
        start=date(2024, 1, 1),
        end=date(2024, 1, 2),
        markets=["US"],
        max_new_symbols=1,
        session=db_session,
        throttle_seconds=0.0,
    )
    db_session.flush()
    assert len(provider.calls) == 1
    ym = utc_year_month()
    assert (
        ProviderHistorySymbolRepository(db_session).count_by_month(
            provider="fake",
            year_month=ym,
        )
        == 1
    )
