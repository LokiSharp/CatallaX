"""Sync provider instrument lists into Security Master tables."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import TYPE_CHECKING

from catallax.db.repositories.instrument import InstrumentRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.db.session import get_engine, session_scope
from catallax.domain.enums import SyncEntity
from catallax.providers.factory import build_instrument_provider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from catallax.providers.base import MarketDataProvider, ProviderInstrument

logger = logging.getLogger(__name__)


def persist_provider_instruments(
    session: Session,
    items: Sequence[ProviderInstrument],
) -> int:
    """Upsert instruments and symbol maps. Returns number of instruments written."""
    instruments = InstrumentRepository(session)
    maps = InstrumentSymbolMapRepository(session)
    written = 0
    for item in items:
        symbol = item.symbol or item.provider_symbol
        row = instruments.upsert_by_business_key(
            symbol=symbol,
            name_cn=item.name_cn,
            name_en=item.name_en,
            market=item.market,
            exchange=item.exchange,
            currency=item.currency,
            asset_type=item.asset_type,
            list_date=item.list_date,
            delist_date=item.delist_date,
            status=item.status,
        )
        maps.upsert(
            instrument_id=row.id,
            provider=item.provider,
            provider_symbol=item.provider_symbol,
            provider_exchange=item.provider_exchange,
            is_active=True,
        )
        written += 1
    return written


def sync_instruments(
    *,
    provider: MarketDataProvider,
    markets: Sequence[str] | None = None,
    session: Session | None = None,
) -> int:
    """Fetch instruments from ``provider`` and upsert into PostgreSQL.

    If ``session`` is omitted, opens a committed ``session_scope``.
    Returns the number of provider rows processed.
    """

    def _run(active: Session) -> int:
        logs = DataSyncLogRepository(active)
        log = logs.start(
            provider=provider.name,
            entity=SyncEntity.INSTRUMENTS.value,
            details=f"markets={list(markets) if markets else 'ALL'}",
        )
        try:
            items = provider.get_instruments(markets=markets)
            count = persist_provider_instruments(active, items)
            # After fallback, provider.name may reflect the source that served data.
            log.provider = provider.name
            logs.mark_success(log, records_written=count)
        except Exception as exc:
            logs.mark_failed(log, error_message=str(exc))
            raise
        else:
            logger.info(
                "sync_instruments provider=%s markets=%s written=%s",
                provider.name,
                markets,
                count,
            )
            return count

    if session is not None:
        return _run(session)
    with session_scope() as scoped:
        return _run(scoped)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry: ``uv run python -m catallax.pipeline.sync_instruments``."""
    parser = argparse.ArgumentParser(
        description="Sync instrument master (default: Longbridge, AKShare fallback)",
    )
    parser.add_argument(
        "--markets",
        default="CN,US",
        help="Comma-separated markets (default: CN,US)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="longbridge | longbridge-only | akshare (default: settings)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]
    provider = build_instrument_provider(args.provider)
    try:
        count = sync_instruments(provider=provider, markets=markets)
        print(f"sync_instruments complete: {count} rows from {provider.name}")
        return 0
    finally:
        get_engine().dispose()


if __name__ == "__main__":
    sys.exit(main())
