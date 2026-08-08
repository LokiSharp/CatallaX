"""PostgreSQL tests for fundamental_period + sync."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from catallax.db.repositories.fundamental import FundamentalPeriodRepository
from catallax.db.repositories.instrument import InstrumentRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.domain.enums import Market, SyncEntity, SyncStatus
from catallax.pipeline.sync_fundamentals import sync_fundamentals
from catallax.providers.base import ProviderFundamentalPeriod
from catallax.providers.longbridge.fundamentals import FUNDAMENTAL_SOURCE

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


class _FakeFundamentalProvider:
    def __init__(self, rows: dict[str, list[ProviderFundamentalPeriod]]) -> None:
        self._rows = rows
        self.calls: list[str] = []

    @property
    def name(self) -> str:
        return "fake"

    def get_fundamental_periods(
        self,
        *,
        provider_symbol: str,
    ) -> list[ProviderFundamentalPeriod]:
        self.calls.append(provider_symbol)
        return list(self._rows.get(provider_symbol, []))


def _seed_map(session: Session) -> int:
    inst = InstrumentRepository(session).create(
        symbol="AAPL",
        market=Market.US.value,
        exchange="NASDAQ",
        name_cn="苹果",
        currency="USD",
    )
    session.flush()
    InstrumentSymbolMapRepository(session).create(
        instrument_id=inst.id,
        provider="fake",
        provider_symbol="AAPL.US",
        provider_exchange="",
    )
    session.flush()
    return inst.id


def test_upsert_and_list(db_session: Session) -> None:
    instrument_id = _seed_map(db_session)
    repo = FundamentalPeriodRepository(db_session)
    repo.upsert(
        instrument_id=instrument_id,
        period_end=date(2024, 6, 29),
        period_label="Q3 2024",
        source=FUNDAMENTAL_SOURCE,
        currency="USD",
        eps=Decimal("1.4"),
        bps=Decimal("4.5"),
        fiscal_year=2024,
        available_date=None,
    )
    repo.upsert(
        instrument_id=instrument_id,
        period_end=date(2024, 6, 29),
        period_label="Q3 2024",
        source=FUNDAMENTAL_SOURCE,
        currency="USD",
        eps=Decimal("1.41"),
        bps=Decimal("4.5"),
        fiscal_year=2024,
    )
    db_session.flush()
    rows = repo.list_by_instrument(instrument_id, source=FUNDAMENTAL_SOURCE)
    assert len(rows) == 1
    assert rows[0].eps == Decimal("1.41")


def test_latest_as_of_requires_available_date(db_session: Session) -> None:
    instrument_id = _seed_map(db_session)
    repo = FundamentalPeriodRepository(db_session)
    repo.upsert(
        instrument_id=instrument_id,
        period_end=date(2024, 3, 30),
        period_label="Q2 2024",
        source=FUNDAMENTAL_SOURCE,
        currency="USD",
        eps=Decimal("1.0"),
        bps=Decimal("4.0"),
        available_date=None,
    )
    repo.upsert(
        instrument_id=instrument_id,
        period_end=date(2023, 12, 30),
        period_label="Q1 2024",
        source=FUNDAMENTAL_SOURCE,
        currency="USD",
        eps=Decimal("0.9"),
        bps=Decimal("3.9"),
        available_date=date(2024, 2, 1),
    )
    db_session.flush()
    # Without available_date, row is invisible to PIT-safe lookup.
    assert (
        repo.latest_as_of(
            instrument_id=instrument_id,
            as_of_date=date(2024, 6, 1),
            require_available_date=True,
        )
        is not None
    )
    pit = repo.latest_as_of(
        instrument_id=instrument_id,
        as_of_date=date(2024, 6, 1),
        require_available_date=True,
    )
    assert pit is not None
    assert pit.period_end == date(2023, 12, 30)
    assert pit.eps == Decimal("0.9")
    # Before available_date → nothing
    assert (
        repo.latest_as_of(
            instrument_id=instrument_id,
            as_of_date=date(2024, 1, 15),
            require_available_date=True,
        )
        is None
    )


def test_sync_fundamentals_idempotent(db_session: Session) -> None:
    _seed_map(db_session)
    period = ProviderFundamentalPeriod(
        provider_symbol="AAPL.US",
        period_end=date(2024, 6, 29),
        period_label="Q3 2024",
        fiscal_year=2024,
        eps=Decimal("1.4"),
        bps=Decimal("4.5"),
        currency="USD",
        announcement_date=None,
        available_date=None,
        source=FUNDAMENTAL_SOURCE,
    )
    provider = _FakeFundamentalProvider({"AAPL.US": [period]})
    first = sync_fundamentals(
        provider=provider,
        markets=["US"],
        symbols=["AAPL"],
        session=db_session,
        throttle_seconds=0.0,
    )
    second = sync_fundamentals(
        provider=provider,
        markets=["US"],
        symbols=["AAPL"],
        session=db_session,
        throttle_seconds=0.0,
    )
    db_session.flush()
    assert first == 1
    assert second == 1
    log = DataSyncLogRepository(db_session).get_latest(
        provider="fake",
        entity=SyncEntity.FUNDAMENTALS.value,
    )
    assert log is not None
    assert log.status == SyncStatus.SUCCESS.value
