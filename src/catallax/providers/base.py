"""Provider protocol and normalized instrument DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date


@dataclass(frozen=True, slots=True)
class ProviderInstrument:
    """Instrument row as returned by a provider *before* internal mapping.

    This is still provider-aware (codes/exchanges as the upstream uses them).
    The normalizer turns it into CatallaX ``instrument`` + ``instrument_symbol_map``.
    """

    provider: str
    provider_symbol: str
    provider_exchange: str
    name_cn: str
    name_en: str
    market: str
    # CatallaX-normalized exchange code (SSE/SZSE/NASDAQ/NYSE/...) when known.
    exchange: str
    currency: str
    asset_type: str
    list_date: date | None = None
    delist_date: date | None = None
    status: str = "active"
    # Canonical display symbol stored on instrument.symbol.
    symbol: str | None = None


@runtime_checkable
class MarketDataProvider(Protocol):
    """Abstract market-data source. Strategies must never call this layer."""

    @property
    def name(self) -> str:
        """Stable provider identifier (e.g. ``akshare``)."""
        ...

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        """Return the security master snapshot for the given markets.

        ``markets`` uses CatallaX market codes (``CN``, ``US``). ``None`` means
        all markets supported by the provider.
        """
        ...
