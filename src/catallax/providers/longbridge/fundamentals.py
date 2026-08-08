"""Parse Longbridge ``financial_report`` into per-period EPS/BPS rows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from catallax.providers.base import ProviderFundamentalPeriod

FUNDAMENTAL_SOURCE = "longbridge:financial_report"


def _fp_end_to_date(raw: object) -> date | None:
    """Convert Longbridge ``fp_end`` (unix seconds string/int) to a date."""
    if raw is None or raw == "":
        return None
    try:
        ts = int(str(raw))
    except ValueError:
        return None
    return datetime.fromtimestamp(ts, tz=UTC).date()


def _to_decimal(raw: object) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return None
    except ValueError:
        return None


def _is_quarter_label(label: str) -> bool:
    """Accept labels like ``Q1 2024`` … ``Q4 2026`` only."""
    parts = label.strip().split()
    if len(parts) != 2:
        return False
    q, year = parts[0].upper(), parts[1]
    if q not in {"Q1", "Q2", "Q3", "Q4"}:
        return False
    return year.isdigit() and len(year) == 4


def _apply_value(
    by_end: dict[date, dict[str, object]],
    *,
    field: str,
    raw: dict[str, Any],
    currency: str,
) -> None:
    """Merge one EPS/BPS value dict into ``by_end``."""
    label = str(raw.get("period") or "").strip()
    if not _is_quarter_label(label):
        return
    period_end = _fp_end_to_date(raw.get("fp_end"))
    if period_end is None:
        return
    slot = by_end.setdefault(
        period_end,
        {
            "period_label": label,
            "fiscal_year": None,
            "eps": None,
            "bps": None,
            "currency": currency,
        },
    )
    year_raw = raw.get("year")
    if year_raw is not None and str(year_raw).isdigit():
        slot["fiscal_year"] = int(str(year_raw))
    slot["period_label"] = label
    slot["currency"] = currency
    val = _to_decimal(raw.get("value"))
    if field == "EPS":
        slot["eps"] = val
    else:
        slot["bps"] = val


def _walk_account(
    by_end: dict[date, dict[str, object]],
    acc: dict[str, Any],
    *,
    currency: str,
) -> None:
    field = str(acc.get("field") or "").strip().upper()
    if field not in {"EPS", "BPS"}:
        return
    values_obj: object = acc.get("values")
    if not isinstance(values_obj, list):
        return
    values_list = cast("list[object]", values_obj)
    for raw_obj in values_list:
        if isinstance(raw_obj, dict):
            _apply_value(
                by_end,
                field=field,
                raw=cast("dict[str, Any]", raw_obj),
                currency=currency,
            )


def _walk_indicator(
    by_end: dict[date, dict[str, object]],
    ind: dict[str, Any],
) -> None:
    currency = str(ind.get("currency") or "USD").strip().upper() or "USD"
    accounts_obj: object = ind.get("accounts")
    if not isinstance(accounts_obj, list):
        return
    for acc_obj in cast("list[object]", accounts_obj):
        if isinstance(acc_obj, dict):
            _walk_account(
                by_end,
                cast("dict[str, Any]", acc_obj),
                currency=currency,
            )


def _walk_report_list(
    report_list: dict[str, Any],
) -> dict[date, dict[str, object]]:
    """Collect EPS/BPS slots keyed by period_end."""
    by_end: dict[date, dict[str, object]] = {}
    for block_obj in report_list.values():
        if not isinstance(block_obj, dict):
            continue
        block = cast("dict[str, Any]", block_obj)
        indicators_obj: object = block.get("indicators")
        if not isinstance(indicators_obj, list):
            continue
        for ind_obj in cast("list[object]", indicators_obj):
            if isinstance(ind_obj, dict):
                _walk_indicator(by_end, cast("dict[str, Any]", ind_obj))
    return by_end


def _slots_to_rows(
    provider_symbol: str,
    by_end: dict[date, dict[str, object]],
) -> list[ProviderFundamentalPeriod]:
    rows: list[ProviderFundamentalPeriod] = []
    for period_end, slot in sorted(by_end.items(), key=lambda item: item[0]):
        eps_obj = slot["eps"]
        bps_obj = slot["bps"]
        eps = eps_obj if isinstance(eps_obj, Decimal) else None
        bps = bps_obj if isinstance(bps_obj, Decimal) else None
        if eps is None and bps is None:
            continue
        fy = slot["fiscal_year"]
        rows.append(
            ProviderFundamentalPeriod(
                provider_symbol=provider_symbol.strip().upper(),
                period_end=period_end,
                period_label=str(slot["period_label"]),
                fiscal_year=fy if isinstance(fy, int) else None,
                eps=eps,
                bps=bps,
                currency=str(slot["currency"]),
                announcement_date=None,
                available_date=None,
                source=FUNDAMENTAL_SOURCE,
            ),
        )
    return rows


def extract_eps_bps_periods(
    provider_symbol: str,
    report_list: object,
) -> list[ProviderFundamentalPeriod]:
    """Build merged EPS/BPS rows keyed by ``period_end`` from a report list dict.

    Longbridge currently does not provide ``announcement_date`` /
    ``available_date`` on these values; both are left NULL (do not invent).
    """
    if not isinstance(report_list, dict):
        return []
    by_end = _walk_report_list(cast("dict[str, Any]", report_list))
    return _slots_to_rows(provider_symbol, by_end)
