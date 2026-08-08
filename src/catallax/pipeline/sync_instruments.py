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
from catallax.domain.markets import DEFAULT_MARKETS
from catallax.progress import ProgressLine
from catallax.providers.factory import build_instrument_provider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from catallax.providers.base import MarketDataProvider, ProviderInstrument

logger = logging.getLogger(__name__)

# Refresh the single-line persist bar every N rows.
_PERSIST_PROGRESS_EVERY = 50


def persist_provider_instruments(
    session: Session,
    items: Sequence[ProviderInstrument],
) -> int:
    """Upsert instruments and symbol maps. Returns number of instruments written."""
    instruments = InstrumentRepository(session)
    maps = InstrumentSymbolMapRepository(session)
    total = len(items)
    written = 0
    progress = ProgressLine()
    if total:
        progress.update(f"persist 0/{total}")
    for item in items:
        symbol = item.symbol or item.provider_symbol
        row = instruments.upsert_by_business_key(
            symbol=symbol,
            market=item.market,
            exchange=item.exchange,
            name_cn=item.name_cn,
            name_en=item.name_en,
            name_hk=item.name_hk,
            currency=item.currency,
        )
        maps.upsert(
            instrument_id=row.id,
            provider=item.provider,
            provider_symbol=item.provider_symbol,
            provider_exchange=item.provider_exchange,
            is_active=True,
        )
        written += 1
        if written == total or written % _PERSIST_PROGRESS_EVERY == 0:
            progress.update(f"persist {written}/{total}")
    progress.finish(f"persisted {written} instruments")
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
        market_label = list(markets) if markets else "ALL"
        logs = DataSyncLogRepository(active)
        log = logs.start(
            provider=provider.name,
            entity=SyncEntity.INSTRUMENTS.value,
            details=f"markets={market_label}",
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
            return count

    if session is not None:
        return _run(session)
    with session_scope() as scoped:
        return _run(scoped)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry: ``uv run python -m catallax.pipeline.sync_instruments``."""
    parser = argparse.ArgumentParser(
        description="Sync instrument master via Longbridge OpenAPI",
    )
    parser.add_argument(
        "--markets",
        default=",".join(DEFAULT_MARKETS),
        help=f"Comma-separated markets (default: {','.join(DEFAULT_MARKETS)})",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider name (default: settings / longbridge)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    # Default WARNING: progress goes to a single stderr line; -v enables INFO logs.
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
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
