"""Resolve the market-data provider from settings."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from catallax.config import settings
from catallax.providers.longbridge.provider import LongbridgeMarketDataProvider

if TYPE_CHECKING:
    from catallax.providers.base import DailyPriceProvider, MarketDataProvider

logger = logging.getLogger(__name__)


def build_instrument_provider(name: str | None = None) -> MarketDataProvider:
    """Build provider for instrument sync (Longbridge only)."""
    return _build_longbridge(name, purpose="instrument")


def build_price_provider(name: str | None = None) -> DailyPriceProvider:
    """Build provider for daily price sync (Longbridge only)."""
    return _build_longbridge(name, purpose="price")


def _build_longbridge(
    name: str | None,
    *,
    purpose: str,
) -> LongbridgeMarketDataProvider:
    choice = (name or settings.market_data_provider).strip().lower()
    if choice in {"longbridge", "lb", "auto", "default", ""}:
        logger.info("using %s provider: longbridge", purpose)
        return LongbridgeMarketDataProvider()
    msg = f"unknown market_data_provider={choice!r}; only 'longbridge' is supported"
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
