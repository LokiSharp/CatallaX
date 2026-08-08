"""Resolve the default market-data provider from settings."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from catallax.config import settings
from catallax.providers.akshare.provider import AkshareMarketDataProvider
from catallax.providers.fallback import FallbackMarketDataProvider
from catallax.providers.longbridge.provider import LongbridgeMarketDataProvider

if TYPE_CHECKING:
    from catallax.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


def build_instrument_provider(name: str | None = None) -> MarketDataProvider:
    """Build provider for instrument sync.

    Default (``longbridge``): Longbridge primary, AKShare fallback.
    ``akshare``: AKShare only.
    ``longbridge-only``: Longbridge without fallback.
    """
    choice = (name or settings.market_data_provider).strip().lower()
    if choice in {"akshare", "ak"}:
        logger.info("using instrument provider: akshare")
        return AkshareMarketDataProvider()
    if choice in {"longbridge-only", "lb-only"}:
        logger.info("using instrument provider: longbridge (no fallback)")
        return LongbridgeMarketDataProvider()
    if choice in {"longbridge", "lb", "auto", "default"}:
        logger.info(
            "using instrument provider: longbridge (fallback=akshare)",
        )
        return FallbackMarketDataProvider(
            LongbridgeMarketDataProvider(),
            AkshareMarketDataProvider(),
        )
    msg = (
        f"unknown market_data_provider={choice!r}; "
        "use longbridge | longbridge-only | akshare"
    )
    raise ValueError(msg)


def longbridge_credentials_configured() -> bool:
    """True if CatallaX settings or LONGBRIDGE_* env can authenticate."""
    if (
        settings.longbridge_app_key
        and settings.longbridge_app_secret
        and settings.longbridge_access_token
    ):
        return True
    return bool(
        os.environ.get("LONGBRIDGE_APP_KEY")
        and os.environ.get("LONGBRIDGE_APP_SECRET")
        and os.environ.get("LONGBRIDGE_ACCESS_TOKEN")
    )
