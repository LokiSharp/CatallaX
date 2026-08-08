"""Cheap, deterministic OHLC sanity checks for daily bars."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from decimal import Decimal


def ohlc_validation_errors(
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    amount: Decimal | None = None,
) -> list[str]:
    """Return human-readable problems; empty list means the bar is acceptable."""
    errors: list[str] = []
    for name, value in (
        ("open", open_),
        ("high", high),
        ("low", low),
        ("close", close),
    ):
        if value <= 0:
            errors.append(f"{name} must be positive")
    if high < low:
        errors.append("high < low")
    if high < open_ or high < close:
        errors.append("high below open/close")
    if low > open_ or low > close:
        errors.append("low above open/close")
    if volume < 0:
        errors.append("volume negative")
    if amount is not None and amount < 0:
        errors.append("amount negative")
    return errors


def is_valid_ohlc(
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    amount: Decimal | None = None,
) -> bool:
    """True when ``ohlc_validation_errors`` is empty."""
    return not ohlc_validation_errors(
        open_=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        amount=amount,
    )
