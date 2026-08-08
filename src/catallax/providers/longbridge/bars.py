"""Daily-bar helpers for Longbridge history candlesticks."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from catallax.providers.longbridge.symbols import parse_longbridge_symbol

if TYPE_CHECKING:
    from collections.abc import Iterator

    from longbridge.openapi import Candlestick

# History API returns at most ~1000 bars; stay under that for daily windows.
DATE_WINDOW_DAYS = 900

# Encodes ForwardAdjust in daily_price.source (no separate adjust column).
DAILY_BAR_SOURCE = "longbridge:forward"

_MARKET_TZ: dict[str, ZoneInfo] = {
    "US": ZoneInfo("America/New_York"),
    "CN": ZoneInfo("Asia/Shanghai"),
    "HK": ZoneInfo("Asia/Hong_Kong"),
    "SG": ZoneInfo("Asia/Singapore"),
}


def iter_date_windows(start: date, end: date) -> Iterator[tuple[date, date]]:
    """Yield inclusive ``(window_start, window_end)`` segments ≤ DATE_WINDOW_DAYS."""
    if end < start:
        msg = f"end {end} is before start {start}"
        raise ValueError(msg)
    cursor = start
    step = timedelta(days=DATE_WINDOW_DAYS - 1)
    while cursor <= end:
        window_end = min(cursor + step, end)
        yield cursor, window_end
        cursor = window_end + timedelta(days=1)


def trade_date_from_timestamp(ts: datetime, *, market: str) -> date:
    """Map candlestick timestamp to a calendar trade date in the market TZ."""
    aware = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts
    tz = _MARKET_TZ.get(market.upper(), UTC)
    return aware.astimezone(tz).date()


def market_for_provider_symbol(provider_symbol: str) -> str:
    """CatallaX market code from a Longbridge ``ticker.region`` symbol."""
    market, _region, _bare = parse_longbridge_symbol(provider_symbol)
    return market


def candlestick_to_bar_fields(
    candle: Candlestick,
    *,
    provider_symbol: str,
) -> tuple[date, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal | None]:
    """Extract ``(trade_date, o, h, l, c, volume, amount)`` from one candle."""
    market = market_for_provider_symbol(provider_symbol)
    trade_date = trade_date_from_timestamp(candle.timestamp, market=market)
    open_ = Decimal(str(candle.open))
    high = Decimal(str(candle.high))
    low = Decimal(str(candle.low))
    close = Decimal(str(candle.close))
    volume = Decimal(str(candle.volume))
    amount = Decimal(str(candle.turnover))
    return trade_date, open_, high, low, close, volume, amount
