"""Unit tests for OHLC validation and sync date-range defaults."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from catallax.domain.ohlc import is_valid_ohlc, ohlc_validation_errors
from catallax.pipeline.date_range import resolve_sync_date_range


def test_valid_ohlc() -> None:
    assert is_valid_ohlc(
        open_=Decimal(100),
        high=Decimal(110),
        low=Decimal(90),
        close=Decimal(105),
        volume=Decimal(1000),
        amount=Decimal(1),
    )


def test_high_below_low() -> None:
    errs = ohlc_validation_errors(
        open_=Decimal(100),
        high=Decimal(90),
        low=Decimal(95),
        close=Decimal(100),
        volume=Decimal(1),
    )
    assert any("high < low" in e for e in errs)


def test_non_positive_price() -> None:
    errs = ohlc_validation_errors(
        open_=Decimal(0),
        high=Decimal(1),
        low=Decimal(1),
        close=Decimal(1),
        volume=Decimal(1),
    )
    assert any("open" in e for e in errs)


def test_high_not_covering_open_close() -> None:
    errs = ohlc_validation_errors(
        open_=Decimal(100),
        high=Decimal(99),
        low=Decimal(90),
        close=Decimal(95),
        volume=Decimal(1),
    )
    assert any("high below" in e for e in errs)


def test_negative_volume() -> None:
    errs = ohlc_validation_errors(
        open_=Decimal(1),
        high=Decimal(1),
        low=Decimal(1),
        close=Decimal(1),
        volume=Decimal(-1),
    )
    assert any("volume" in e for e in errs)


def test_resolve_both_dates() -> None:
    assert resolve_sync_date_range(
        date(2024, 1, 1),
        date(2024, 1, 10),
    ) == (date(2024, 1, 1), date(2024, 1, 10))


def test_resolve_default_lookback() -> None:
    start, end = resolve_sync_date_range(
        None,
        None,
        days=10,
        today=date(2024, 6, 15),
    )
    assert end == date(2024, 6, 15)
    assert start == date(2024, 6, 6)


def test_resolve_only_end() -> None:
    start, end = resolve_sync_date_range(
        None,
        date(2024, 1, 10),
        days=5,
    )
    assert (start, end) == (date(2024, 1, 6), date(2024, 1, 10))


def test_resolve_only_start() -> None:
    start, end = resolve_sync_date_range(
        date(2024, 1, 1),
        None,
        days=3,
    )
    assert (start, end) == (date(2024, 1, 1), date(2024, 1, 3))


def test_resolve_end_before_start() -> None:
    with pytest.raises(ValueError, match="before"):
        resolve_sync_date_range(date(2024, 2, 1), date(2024, 1, 1))
