"""Longbridge OpenAPI implementation of MarketDataProvider (instruments)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from longbridge.openapi import Config, Market, QuoteContext

from catallax.config import settings
from catallax.domain.enums import AssetType, InstrumentStatus
from catallax.providers.base import ProviderInstrument
from catallax.providers.longbridge.symbols import (
    currency_for_market,
    parse_longbridge_symbol,
)

logger = logging.getLogger(__name__)

PROVIDER_NAME = "longbridge"

# (longbridge_symbol, display_name) rows for injectability in tests.
SecurityRow = tuple[str, str]
ListFetcher = Callable[[str], list[SecurityRow]]


class LongbridgeMarketDataProvider:
    """Fetch security lists from Longbridge OpenAPI.

    Requires credentials via settings / env:
    ``CATALLAX_LONGBRIDGE_APP_KEY``, ``CATALLAX_LONGBRIDGE_APP_SECRET``,
    ``CATALLAX_LONGBRIDGE_ACCESS_TOKEN`` (or native ``LONGBRIDGE_*`` vars).
    """

    def __init__(
        self,
        *,
        list_fetcher: ListFetcher | None = None,
    ) -> None:
        self._list_fetcher = list_fetcher

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        wanted = {m.upper() for m in markets} if markets else {"CN", "US"}
        lb_markets: list[str] = []
        if "US" in wanted:
            lb_markets.append("US")
        if "CN" in wanted:
            lb_markets.append("CN")
        if "HK" in wanted:
            lb_markets.append("HK")

        out: list[ProviderInstrument] = []
        for lb_market in lb_markets:
            rows = self._fetch_market(lb_market)
            for lb_symbol, name in rows:
                item = _to_provider_instrument(lb_symbol, name)
                if item.market in wanted:
                    out.append(item)
        logger.info("Longbridge instruments fetched: %s", len(out))
        return out

    def _fetch_market(self, market: str) -> list[SecurityRow]:
        if self._list_fetcher is not None:
            return self._list_fetcher(market)
        return _fetch_security_list_live(market)


def _to_provider_instrument(lb_symbol: str, name: str) -> ProviderInstrument:
    market, exchange, bare = parse_longbridge_symbol(lb_symbol)
    display = name.strip() or bare
    return ProviderInstrument(
        provider=PROVIDER_NAME,
        provider_symbol=lb_symbol.strip().upper(),
        provider_exchange=exchange,
        name=display,
        market=market,
        exchange=exchange,
        currency=currency_for_market(market),
        asset_type=AssetType.EQUITY.value,
        status=InstrumentStatus.ACTIVE.value,
        symbol=bare,
    )


def _fetch_security_list_live(market: str) -> list[SecurityRow]:
    """Call Longbridge ``security_list`` for one market."""
    config = _build_config()
    ctx = QuoteContext(config)
    market_enum = {
        "US": Market.US,
        "CN": Market.CN,
        "HK": Market.HK,
    }.get(market.upper())
    if market_enum is None:
        msg = f"unsupported Longbridge market: {market}"
        raise ValueError(msg)

    securities = ctx.security_list(market_enum)
    rows: list[SecurityRow] = []
    for sec in securities:
        sym = str(sec.symbol).strip()
        name = (
            str(sec.name_cn).strip()
            or str(sec.name_en).strip()
            or str(sec.name_hk).strip()
            or sym
        )
        if sym:
            rows.append((sym, name))
    return rows


def _build_config() -> Config:
    """Build Longbridge Config from CatallaX settings or process env."""
    app_key = settings.longbridge_app_key.strip()
    app_secret = settings.longbridge_app_secret.strip()
    access_token = settings.longbridge_access_token.strip()
    if app_key and app_secret and access_token:
        return Config.from_apikey(app_key, app_secret, access_token)
    return Config.from_apikey_env()
