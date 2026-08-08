"""PostgreSQL integration tests for instrument sync (mocked provider)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from catallax.db.repositories.instrument import InstrumentRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.domain.enums import AssetType, Market, SyncEntity, SyncStatus
from catallax.pipeline.sync_instruments import sync_instruments
from catallax.providers.base import ProviderInstrument

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


class _FakeProvider:
    def __init__(self, items: list[ProviderInstrument]) -> None:
        self._items = items

    @property
    def name(self) -> str:
        return "fake"

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        if markets is None:
            return list(self._items)
        wanted = {m.upper() for m in markets}
        return [i for i in self._items if i.market in wanted]


def _sample_items() -> list[ProviderInstrument]:
    return [
        ProviderInstrument(
            provider="fake",
            provider_symbol="600519",
            provider_exchange="SH",
            name="贵州茅台",
            market=Market.CN.value,
            exchange="SSE",
            currency="CNY",
            asset_type=AssetType.EQUITY.value,
            symbol="600519",
        ),
        ProviderInstrument(
            provider="fake",
            provider_symbol="AAPL",
            provider_exchange="",
            name="Apple Inc.",
            market=Market.US.value,
            exchange="US",
            currency="USD",
            asset_type=AssetType.EQUITY.value,
            symbol="AAPL",
        ),
    ]


def test_sync_instruments_idempotent(db_session: Session) -> None:
    provider = _FakeProvider(_sample_items())

    first = sync_instruments(provider=provider, session=db_session)
    second = sync_instruments(provider=provider, session=db_session)
    db_session.flush()

    assert first == 2
    assert second == 2

    instruments = InstrumentRepository(db_session)
    assert len(instruments.list_by_market(Market.CN.value)) == 1
    assert len(instruments.list_by_market(Market.US.value)) == 1

    moutai = instruments.get_by_business_key(
        market=Market.CN.value,
        exchange="SSE",
        symbol="600519",
    )
    assert moutai is not None
    maps = InstrumentSymbolMapRepository(db_session).list_by_instrument(moutai.id)
    assert len(maps) == 1
    assert maps[0].provider == "fake"
    assert maps[0].provider_symbol == "600519"

    log = DataSyncLogRepository(db_session).get_latest(
        provider="fake",
        entity=SyncEntity.INSTRUMENTS.value,
    )
    assert log is not None
    assert log.status == SyncStatus.SUCCESS.value
    assert log.records_written == 2


def test_sync_instruments_updates_name_on_rerun(db_session: Session) -> None:
    items = _sample_items()
    sync_instruments(provider=_FakeProvider(items), session=db_session)

    updated = [
        ProviderInstrument(
            provider="fake",
            provider_symbol="600519",
            provider_exchange="SH",
            name="Kweichow Moutai",
            market=Market.CN.value,
            exchange="SSE",
            currency="CNY",
            asset_type=AssetType.EQUITY.value,
            symbol="600519",
        ),
    ]
    sync_instruments(
        provider=_FakeProvider(updated),
        markets=["CN"],
        session=db_session,
    )
    db_session.flush()

    row = InstrumentRepository(db_session).get_by_business_key(
        market=Market.CN.value,
        exchange="SSE",
        symbol="600519",
    )
    assert row is not None
    assert row.name == "Kweichow Moutai"
