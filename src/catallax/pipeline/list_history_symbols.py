"""List locally recorded history-K query symbols (monthly quota ledger)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

from catallax.db.repositories.history_symbol import (
    ProviderHistorySymbolRepository,
    utc_year_month,
)
from catallax.db.session import get_engine, session_scope
from catallax.providers.longbridge.provider import PROVIDER_NAME

if TYPE_CHECKING:
    from collections.abc import Sequence


def list_history_symbols(
    *,
    provider: str = PROVIDER_NAME,
    year_month: str | None = None,
) -> list[dict[str, object]]:
    """Return ledger rows as plain dicts for the given UTC month."""
    ym = year_month or utc_year_month()
    with session_scope() as session:
        repo = ProviderHistorySymbolRepository(session)
        rows = repo.list_by_month(provider=provider, year_month=ym)
        return [
            {
                "provider": r.provider,
                "provider_symbol": r.provider_symbol,
                "year_month": r.year_month,
                "instrument_id": r.instrument_id,
                "first_queried_at": r.first_queried_at.isoformat(),
                "last_queried_at": r.last_queried_at.isoformat(),
                "query_count": r.query_count,
            }
            for r in rows
        ]


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: ``uv run python -m catallax.pipeline.list_history_symbols``."""
    parser = argparse.ArgumentParser(
        description=(
            "List symbols recorded in provider_history_symbol for a UTC month. "
            "This is a local estimate of Longbridge monthly history-K unique symbols."
        ),
    )
    parser.add_argument(
        "--provider",
        default=PROVIDER_NAME,
        help=f"Provider name (default: {PROVIDER_NAME})",
    )
    parser.add_argument(
        "--month",
        default=None,
        help="UTC year-month YYYY-MM (default: current UTC month)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON array instead of a table",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    ym = args.month or utc_year_month()
    try:
        rows = list_history_symbols(provider=args.provider, year_month=ym)
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print(f"provider={args.provider} year_month={ym} count={len(rows)}")
            if rows:
                print(
                    f"{'provider_symbol':<16} {'instrument_id':>14} "
                    f"{'query_count':>11} first_queried_at",
                )
                for r in rows:
                    print(
                        f"{r['provider_symbol']!s:<16} "
                        f"{(r['instrument_id'] or '-')!s:>14} "
                        f"{r['query_count']:>11} {r['first_queried_at']}",
                    )
        return 0
    finally:
        get_engine().dispose()


if __name__ == "__main__":
    sys.exit(main())
