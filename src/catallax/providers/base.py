"""Provider protocol and normalized instrument / bar DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import date
    from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ProviderInstrument:
    """Instrument row as returned by a provider *before* internal mapping.

    This is still provider-aware (codes/exchanges as the upstream uses them).
    The normalizer turns it into CatallaX ``instrument`` + ``instrument_symbol_map``.
    """

    provider: str
    provider_symbol: str
    provider_exchange: str
    market: str
    # CatallaX-normalized exchange code (SSE/SZSE/NASDAQ/NYSE/...) when known.
    exchange: str
    name_cn: str
    name_en: str
    name_hk: str
    currency: str
    # Canonical display symbol stored on instrument.symbol.
    symbol: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderDailyBar:
    """One daily OHLCV bar from a provider before internal instrument_id mapping."""

    provider_symbol: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None
    source: str


@runtime_checkable
class MarketDataProvider(Protocol):
    """Abstract market-data source. Strategies must never call this layer."""

    @property
    def name(self) -> str:
        """Stable provider identifier (e.g. ``longbridge``)."""
        ...

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        """Return the security master snapshot for the given markets.

        ``markets`` uses CatallaX market codes (``CN``, ``US``, ``HK``).
        ``None`` means the provider default set.
        """
        ...


@runtime_checkable
class DailyPriceProvider(Protocol):
    """Provider that can fetch daily bars. Strategies must never call this."""

    @property
    def name(self) -> str:
        """Stable provider identifier."""
        ...

    def get_daily_bars(
        self,
        *,
        provider_symbol: str,
        start: date,
        end: date,
    ) -> list[ProviderDailyBar]:
        """Daily bars for ``provider_symbol`` in ``[start, end]`` (inclusive)."""
        ...
