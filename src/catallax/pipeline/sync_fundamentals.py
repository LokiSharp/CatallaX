"""Sync fiscal-period EPS/BPS into fundamental_period."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import TYPE_CHECKING

from catallax.db.repositories.fundamental import FundamentalPeriodRepository
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.db.session import get_engine, session_scope
from catallax.domain.enums import SyncEntity
from catallax.progress import ProgressLine
from catallax.providers.factory import build_fundamental_provider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from catallax.db.models.instrument import InstrumentSymbolMap
    from catallax.providers.base import FundamentalProvider

logger = logging.getLogger(__name__)

_LIVE_THROTTLE_SECONDS = 1.0


def _select_targets(
    session: Session,
    *,
    provider_name: str,
    markets: Sequence[str] | None,
    symbols: Sequence[str] | None,
    limit: int | None,
) -> list[InstrumentSymbolMap]:
    return InstrumentSymbolMapRepository(session).list_active_by_provider(
        provider=provider_name,
        markets=markets,
        symbols=symbols,
        limit=limit,
    )


def _sync_one(
    *,
    provider: FundamentalProvider,
    mapping: InstrumentSymbolMap,
    repo: FundamentalPeriodRepository,
) -> int:
    periods = provider.get_fundamental_periods(
        provider_symbol=mapping.provider_symbol,
    )
    written = 0
    for row in periods:
        repo.upsert(
            instrument_id=mapping.instrument_id,
            period_end=row.period_end,
            period_label=row.period_label,
            source=row.source,
            currency=row.currency,
            eps=row.eps,
            bps=row.bps,
            fiscal_year=row.fiscal_year,
            announcement_date=row.announcement_date,
            available_date=row.available_date,
        )
        written += 1
    return written


def sync_fundamentals(
    *,
    provider: FundamentalProvider,
    markets: Sequence[str] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
    throttle_seconds: float = 0.0,
    session: Session | None = None,
) -> int:
    """Fetch fiscal-period metrics and upsert. Returns period rows written."""

    def _run(active: Session) -> int:
        details = (
            f"markets={list(markets) if markets else 'ALL'} "
            f"symbols={list(symbols) if symbols else 'ALL'} limit={limit}"
        )
        logs = DataSyncLogRepository(active)
        log = logs.start(
            provider=provider.name,
            entity=SyncEntity.FUNDAMENTALS.value,
            details=details,
        )
        repo = FundamentalPeriodRepository(active)
        try:
            targets = _select_targets(
                active,
                provider_name=provider.name,
                markets=markets,
                symbols=symbols,
                limit=limit,
            )
            progress = ProgressLine()
            total = len(targets)
            written = 0
            failures: list[str] = []
            if total == 0:
                progress.finish("no instruments matched filters")
            for idx, mapping in enumerate(targets, start=1):
                sym = mapping.provider_symbol
                progress.update(f"fundamentals {idx}/{total} {sym}")
                try:
                    written += _sync_one(
                        provider=provider,
                        mapping=mapping,
                        repo=repo,
                    )
                except Exception as exc:
                    logger.exception("fundamentals failed for %s", sym)
                    failures.append(f"{sym}: {exc}")
                if throttle_seconds > 0 and idx < total:
                    time.sleep(throttle_seconds)
            progress.finish(
                f"persisted {written} period rows for {total} symbols"
                + (f" ({len(failures)} failed)" if failures else ""),
            )
            if failures:
                log.details = (log.details or "") + f" failures={failures[:20]}"
            logs.mark_success(log, records_written=written)
        except Exception as exc:
            logs.mark_failed(log, error_message=str(exc))
            raise
        else:
            return written

    if session is not None:
        return _run(session)
    with session_scope() as scoped:
        return _run(scoped)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``uv run python -m catallax.pipeline.sync_fundamentals``."""
    parser = argparse.ArgumentParser(
        description=(
            "Sync quarterly EPS/BPS from Longbridge financial_report. "
            "available_date/announcement_date are NULL when upstream omits them "
            "(PIT-safe PE/PB must not use those rows until dates are filled)."
        ),
    )
    parser.add_argument("--markets", default="")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--no-throttle", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()] or None
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None
    provider = build_fundamental_provider(args.provider)
    throttle = 0.0 if args.no_throttle else _LIVE_THROTTLE_SECONDS
    try:
        count = sync_fundamentals(
            provider=provider,
            markets=markets,
            symbols=symbols,
            limit=args.limit,
            throttle_seconds=throttle,
        )
        print(f"sync_fundamentals complete: {count} period rows from {provider.name}")
        return 0
    finally:
        get_engine().dispose()


if __name__ == "__main__":
    sys.exit(main())
