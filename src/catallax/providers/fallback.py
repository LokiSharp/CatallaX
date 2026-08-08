"""Primary provider with automatic fallback on failure or empty results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from catallax.providers.base import MarketDataProvider, ProviderInstrument

logger = logging.getLogger(__name__)


class FallbackMarketDataProvider:
    """Try ``primary`` first; on error or empty list use ``fallback``."""

    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._last_used: str = primary.name

    @property
    def name(self) -> str:
        """Report the provider that last successfully returned data."""
        return self._last_used

    @property
    def primary_name(self) -> str:
        return self._primary.name

    @property
    def fallback_name(self) -> str:
        return self._fallback.name

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        try:
            items = self._primary.get_instruments(markets=markets)
            if items:
                self._last_used = self._primary.name
                return items
            logger.warning(
                "primary provider %s returned no instruments; trying %s",
                self._primary.name,
                self._fallback.name,
            )
        except Exception:
            logger.exception(
                "primary provider %s failed; trying %s",
                self._primary.name,
                self._fallback.name,
            )

        items = self._fallback.get_instruments(markets=markets)
        self._last_used = self._fallback.name
        return items
