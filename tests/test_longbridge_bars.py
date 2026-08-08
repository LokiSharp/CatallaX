"""Unit tests for Longbridge daily-bar helpers and injected fetcher."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from catallax.providers.base import ProviderDailyBar
from catallax.providers.longbridge.bars import (
    DAILY_BAR_SOURCE,
    DATE_WINDOW_DAYS,
    iter_date_windows,
    trade_date_from_timestamp,
)
from catallax.providers.longbridge.provider import LongbridgeMarketDataProvider


def test_iter_date_windows_single() -> None:
    windows = list(iter_date_windows(date(2024, 1, 1), date(2024, 1, 10)))
    assert windows == [(date(2024, 1, 1), date(2024, 1, 10))]


def test_iter_date_windows_splits() -> None:
    start = date(2020, 1, 1)
    end = date(2024, 12, 31)
    windows = list(iter_date_windows(start, end))
    assert len(windows) >= 2
    assert windows[0][0] == start
    assert windows[-1][1] == end
    for a, b in windows:
        assert (b - a).days < DATE_WINDOW_DAYS
    for i in range(len(windows) - 1):
        next_start = windows[i][1] + timedelta(days=1)
        assert next_start == windows[i + 1][0]


def test_trade_date_us_evening_utc() -> None:
    # 2024-01-02 21:00 UTC → still 2024-01-02 in America/New_York (EST).
    ts = datetime(2024, 1, 2, 21, 0, 0, tzinfo=UTC)
    assert trade_date_from_timestamp(ts, market="US") == date(2024, 1, 2)


def test_trade_date_hk_from_utc_midnight_boundary() -> None:
    # 2022-04-19 16:00 UTC → 2022-04-20 00:00 HKT (common daily bar stamp).
    ts = datetime(2022, 4, 19, 16, 0, 0, tzinfo=UTC)
    assert trade_date_from_timestamp(ts, market="HK") == date(2022, 4, 20)
    assert trade_date_from_timestamp(ts, market="CN") == date(2022, 4, 20)


def test_trade_date_naive_treated_as_utc() -> None:
    ts = datetime(2024, 6, 1, 12, 0, 0)  # noqa: DTZ001 — intentional naive
    ny = trade_date_from_timestamp(ts, market="US")
    expected = (
        datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        .astimezone(
            ZoneInfo("America/New_York"),
        )
        .date()
    )
    assert ny == expected


def test_get_daily_bars_injected() -> None:
    def fetch(symbol: str, start: date, end: date) -> list[ProviderDailyBar]:
        assert symbol == "AAPL.US"
        assert start == date(2024, 1, 2)
        assert end == date(2024, 1, 3)
        return [
            ProviderDailyBar(
                provider_symbol=symbol,
                trade_date=date(2024, 1, 2),
                open=Decimal(100),
                high=Decimal(110),
                low=Decimal(90),
                close=Decimal(105),
                volume=Decimal(1000),
                amount=Decimal(105000),
                source=DAILY_BAR_SOURCE,
            ),
        ]

    provider = LongbridgeMarketDataProvider(bars_fetcher=fetch)
    bars = provider.get_daily_bars(
        provider_symbol="aapl.us",
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
    )
    assert len(bars) == 1
    assert bars[0].close == Decimal(105)
    assert bars[0].source == DAILY_BAR_SOURCE
