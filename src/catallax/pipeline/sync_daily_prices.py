"""Sync daily OHLCV from a price provider into daily_price."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from typing import TYPE_CHECKING

from catallax.db.repositories.daily_price import DailyPriceRepository
from catallax.db.repositories.history_symbol import (
    ProviderHistorySymbolRepository,
    utc_year_month,
)
from catallax.db.repositories.symbol_map import InstrumentSymbolMapRepository
from catallax.db.repositories.sync_log import DataSyncLogRepository
from catallax.db.session import get_engine, session_scope
from catallax.domain.enums import SyncEntity
from catallax.progress import ProgressLine
from catallax.providers.factory import build_price_provider

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm import Session

    from catallax.db.models.instrument import InstrumentSymbolMap
    from catallax.providers.base import DailyPriceProvider

logger = logging.getLogger(__name__)

# Longbridge history: ~60 requests / 30s → leave headroom between symbols.
_LIVE_THROTTLE_SECONDS = 0.6


def _select_targets(
    session: Session,
    *,
    provider_name: str,
    markets: Sequence[str] | None,
    symbols: Sequence[str] | None,
    limit: int | None,
    only_already_queried: bool,
    max_new_symbols: int | None,
) -> list[InstrumentSymbolMap]:
    maps_repo = InstrumentSymbolMapRepository(session)
    history = ProviderHistorySymbolRepository(session)
    year_month = utc_year_month()
    candidates = maps_repo.list_active_by_provider(
        provider=provider_name,
        markets=markets,
        symbols=symbols,
        limit=None,
    )
    selected: list[InstrumentSymbolMap] = []
    new_count = 0
    for row in candidates:
        already = history.has_query(
            provider=provider_name,
            provider_symbol=row.provider_symbol,
            year_month=year_month,
        )
        if only_already_queried and not already:
            continue
        if not already and max_new_symbols is not None and new_count >= max_new_symbols:
            continue
        if not already:
            new_count += 1
        selected.append(row)
        if limit is not None and len(selected) >= limit:
            break
    return selected


def _sync_one_symbol(
    *,
    provider: DailyPriceProvider,
    mapping: InstrumentSymbolMap,
    start: date,
    end: date,
    prices: DailyPriceRepository,
    history: ProviderHistorySymbolRepository,
) -> int:
    """Fetch and upsert bars for one mapping. Returns bars written."""
    bars = provider.get_daily_bars(
        provider_symbol=mapping.provider_symbol,
        start=start,
        end=end,
    )
    written = 0
    for bar in bars:
        prices.upsert(
            instrument_id=mapping.instrument_id,
            trade_date=bar.trade_date,
            open_=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            amount=bar.amount,
            source=bar.source,
        )
        written += 1
    history.record_query(
        provider=provider.name,
        provider_symbol=mapping.provider_symbol,
        instrument_id=mapping.instrument_id,
    )
    return written


def sync_daily_prices(
    *,
    provider: DailyPriceProvider,
    start: date,
    end: date,
    markets: Sequence[str] | None = None,
    symbols: Sequence[str] | None = None,
    limit: int | None = None,
    only_already_queried: bool = False,
    max_new_symbols: int | None = None,
    throttle_seconds: float = 0.0,
    session: Session | None = None,
) -> int:
    """Fetch daily bars and upsert. Returns number of bar rows written."""

    def _run(active: Session) -> int:
        details = (
            f"start={start} end={end} markets={list(markets) if markets else 'ALL'} "
            f"symbols={list(symbols) if symbols else 'ALL'} limit={limit} "
            f"only_already_queried={only_already_queried} "
            f"max_new_symbols={max_new_symbols}"
        )
        logs = DataSyncLogRepository(active)
        log = logs.start(
            provider=provider.name,
            entity=SyncEntity.DAILY_PRICES.value,
            details=details,
        )
        prices = DailyPriceRepository(active)
        history = ProviderHistorySymbolRepository(active)
        try:
            targets = _select_targets(
                active,
                provider_name=provider.name,
                markets=markets,
                symbols=symbols,
                limit=limit,
                only_already_queried=only_already_queried,
                max_new_symbols=max_new_symbols,
            )
            progress = ProgressLine()
            total_targets = len(targets)
            bars_written = 0
            failures: list[str] = []
            if total_targets == 0:
                progress.finish("no instruments matched filters")
            for idx, mapping in enumerate(targets, start=1):
                sym = mapping.provider_symbol
                progress.update(f"daily {idx}/{total_targets} {sym}")
                try:
                    bars_written += _sync_one_symbol(
                        provider=provider,
                        mapping=mapping,
                        start=start,
                        end=end,
                        prices=prices,
                        history=history,
                    )
                except Exception as exc:
                    logger.exception("daily price failed for %s", sym)
                    failures.append(f"{sym}: {exc}")
                if throttle_seconds > 0 and idx < total_targets:
                    time.sleep(throttle_seconds)
            progress.finish(
                f"persisted {bars_written} bars for {total_targets} symbols"
                + (f" ({len(failures)} failed)" if failures else ""),
            )
            if failures:
                log.details = (log.details or "") + f" failures={failures[:20]}"
            logs.mark_success(log, records_written=bars_written)
        except Exception as exc:
            logs.mark_failed(log, error_message=str(exc))
            raise
        else:
            return bars_written

    if session is not None:
        return _run(session)
    with session_scope() as scoped:
        return _run(scoped)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``uv run python -m catallax.pipeline.sync_daily_prices``."""
    parser = argparse.ArgumentParser(
        description=(
            "Sync daily prices via Longbridge (ForwardAdjust). "
            "Records symbols in provider_history_symbol (monthly quota ledger)."
        ),
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--markets",
        default="",
        help="Comma-separated markets (default: all with longbridge maps)",
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma-separated bare symbols (e.g. AAPL,600519)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max instruments to process",
    )
    parser.add_argument(
        "--max-new-symbols",
        type=int,
        default=None,
        help="Max symbols not yet in this month's history ledger",
    )
    parser.add_argument(
        "--only-already-queried",
        action="store_true",
        help="Only symbols already recorded in this month's ledger",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Provider name (default: settings / longbridge)",
    )
    parser.add_argument(
        "--no-throttle",
        action="store_true",
        help="Disable inter-symbol throttle (default ~0.6s for live API)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()] or None
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] or None
    provider = build_price_provider(args.provider)
    throttle = 0.0 if args.no_throttle else _LIVE_THROTTLE_SECONDS
    try:
        count = sync_daily_prices(
            provider=provider,
            start=start,
            end=end,
            markets=markets,
            symbols=symbols,
            limit=args.limit,
            only_already_queried=args.only_already_queried,
            max_new_symbols=args.max_new_symbols,
            throttle_seconds=throttle,
        )
        print(
            f"sync_daily_prices complete: {count} bars from {provider.name} "
            f"({start}..{end})",
        )
        return 0
    finally:
        get_engine().dispose()


if __name__ == "__main__":
    sys.exit(main())
