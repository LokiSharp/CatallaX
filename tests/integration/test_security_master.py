"""PostgreSQL integration tests for Security Master (Milestone 1.1)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.exc import IntegrityError

from catallax.db.repositories.instrument import InstrumentRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.domain.enums import (
    AssetType,
    InstrumentStatus,
    Market,
    SyncEntity,
    SyncStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _flush_duplicate_instrument(repo: InstrumentRepository, session: Session) -> None:
    repo.create(
        symbol="AAPL",
        name="Apple Duplicate",
        market=Market.US.value,
        exchange="NASDAQ",
        currency="USD",
        asset_type=AssetType.EQUITY.value,
    )
    session.flush()


def _flush_duplicate_symbol_map(
    maps: InstrumentSymbolMapRepository,
    session: Session,
    instrument_id: int,
) -> None:
    maps.create(
        instrument_id=instrument_id,
        provider="akshare",
        provider_symbol="600519",
        provider_exchange="SH",
    )
    session.flush()


def test_instrument_create_and_get(db_session: Session) -> None:
    repo = InstrumentRepository(db_session)
    row = repo.create(
        symbol="600519",
        name="Kweichow Moutai",
        market=Market.CN.value,
        exchange="SSE",
        currency="CNY",
        asset_type=AssetType.EQUITY.value,
        list_date=date(2001, 8, 27),
        status=InstrumentStatus.ACTIVE.value,
    )
    db_session.flush()

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.symbol == "600519"
    assert loaded.market == Market.CN.value
    assert loaded.exchange == "SSE"


def test_instrument_business_key_unique(db_session: Session) -> None:
    repo = InstrumentRepository(db_session)
    repo.create(
        symbol="AAPL",
        name="Apple Inc.",
        market=Market.US.value,
        exchange="NASDAQ",
        currency="USD",
        asset_type=AssetType.EQUITY.value,
    )
    db_session.flush()

    with db_session.begin_nested(), pytest.raises(IntegrityError):
        _flush_duplicate_instrument(repo, db_session)


def test_instrument_upsert_is_idempotent(db_session: Session) -> None:
    repo = InstrumentRepository(db_session)
    first = repo.upsert_by_business_key(
        symbol="AAPL",
        name="Apple Inc.",
        market=Market.US.value,
        exchange="NASDAQ",
        currency="USD",
        asset_type=AssetType.EQUITY.value,
    )
    second = repo.upsert_by_business_key(
        symbol="AAPL",
        name="Apple Inc. Updated",
        market=Market.US.value,
        exchange="NASDAQ",
        currency="USD",
        asset_type=AssetType.EQUITY.value,
    )
    db_session.flush()

    assert first.id == second.id
    assert second.name == "Apple Inc. Updated"
    assert len(repo.list_by_market(Market.US.value)) == 1


def test_instrument_update(db_session: Session) -> None:
    repo = InstrumentRepository(db_session)
    row = repo.create(
        symbol="MSFT",
        name="Microsoft",
        market=Market.US.value,
        exchange="NASDAQ",
        currency="USD",
        asset_type=AssetType.EQUITY.value,
    )
    repo.update(row, name="Microsoft Corporation", status=InstrumentStatus.ACTIVE.value)
    db_session.flush()
    assert repo.get_by_id(row.id) is not None
    assert row.name == "Microsoft Corporation"


def test_symbol_map_unique_and_upsert(db_session: Session) -> None:
    instruments = InstrumentRepository(db_session)
    maps = InstrumentSymbolMapRepository(db_session)

    inst = instruments.create(
        symbol="600519",
        name="Moutai",
        market=Market.CN.value,
        exchange="SSE",
        currency="CNY",
        asset_type=AssetType.EQUITY.value,
    )
    db_session.flush()

    first = maps.upsert(
        instrument_id=inst.id,
        provider="akshare",
        provider_symbol="600519",
        provider_exchange="SH",
        is_active=True,
    )
    second = maps.upsert(
        instrument_id=inst.id,
        provider="akshare",
        provider_symbol="600519",
        provider_exchange="SH",
        is_active=False,
    )
    db_session.flush()

    assert first.id == second.id
    assert second.is_active is False
    assert len(maps.list_by_instrument(inst.id)) == 1

    with db_session.begin_nested(), pytest.raises(IntegrityError):
        _flush_duplicate_symbol_map(maps, db_session, inst.id)


def test_data_sync_log_lifecycle(db_session: Session) -> None:
    repo = DataSyncLogRepository(db_session)
    log = repo.start(
        provider="akshare",
        entity=SyncEntity.INSTRUMENTS.value,
        details="manual test",
    )
    db_session.flush()
    assert log.status == SyncStatus.RUNNING.value

    repo.mark_success(log, records_written=2)
    db_session.flush()
    assert log.status == SyncStatus.SUCCESS.value
    assert log.finished_at is not None
    assert log.records_written == 2

    failed = repo.start(provider="akshare", entity=SyncEntity.INSTRUMENTS.value)
    repo.mark_failed(failed, error_message="boom")
    db_session.flush()
    assert failed.status == SyncStatus.FAILED.value

    latest = repo.get_latest(provider="akshare", entity=SyncEntity.INSTRUMENTS.value)
    assert latest is not None
    assert latest.id == failed.id
