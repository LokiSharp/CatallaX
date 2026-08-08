"""Resolve CLI date windows for daily-price sync."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

# Default lookback when --start/--end omitted (calendar days, inclusive window).
DEFAULT_LOOKBACK_DAYS = 10


def resolve_sync_date_range(
    start: date | None,
    end: date | None,
    *,
    days: int = DEFAULT_LOOKBACK_DAYS,
    today: date | None = None,
) -> tuple[date, date]:
    """Return inclusive ``(start, end)`` for a sync job.

    Rules:
    - Both provided: use as-is (require ``end >= start``).
    - Neither: ``end = today`` (UTC date), ``start = end - (days - 1)``.
    - Only ``end``: ``start = end - (days - 1)``.
    - Only ``start``: ``end = start + (days - 1)``.

    ``days`` is the inclusive span length in **calendar** days (not trading days).
    """
    if days < 1:
        msg = f"days must be >= 1, got {days}"
        raise ValueError(msg)

    if start is not None and end is not None:
        if end < start:
            msg = f"end {end} is before start {start}"
            raise ValueError(msg)
        return start, end

    span = timedelta(days=days - 1)
    if start is None and end is None:
        end_d = today if today is not None else datetime.now(UTC).date()
        return end_d - span, end_d
    if start is not None and end is None:
        return start, start + span
    if start is None and end is not None:
        return end - span, end
    msg = "unreachable date range state"
    raise RuntimeError(msg)
