"""Shared market codes used across providers and CLI defaults."""

from __future__ import annotations

from catallax.domain.enums import Market

# Default instrument-sync universe for CatallaX.
DEFAULT_MARKETS: tuple[str, ...] = (
    Market.CN.value,
    Market.US.value,
    Market.HK.value,
)
