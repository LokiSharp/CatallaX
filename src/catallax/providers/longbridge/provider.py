"""Longbridge OpenAPI implementation of MarketDataProvider (instruments)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from longbridge.openapi import Config, Market, QuoteContext

from catallax.config import settings
from catallax.domain.enums import AssetType, InstrumentStatus
from catallax.providers.base import ProviderInstrument
from catallax.providers.longbridge.symbols import (
    currency_for_market,
    map_longbridge_exchange,
    parse_longbridge_symbol,
)

logger = logging.getLogger(__name__)

PROVIDER_NAME = "longbridge"
_STATIC_INFO_BATCH = 500


@dataclass(frozen=True, slots=True)
class SecurityRow:
    """One Longbridge security after optional static_info enrichment."""

    symbol: str
    name_cn: str
    name_en: str
    exchange: str
    currency: str


ListFetcher = Callable[[str], list[SecurityRow]]


class LongbridgeMarketDataProvider:
    """Fetch security lists from Longbridge OpenAPI.

    Uses ``security_list`` for coverage, then ``static_info`` (batched) for
    real exchange codes and bilingual names when available.
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
            for row in rows:
                item = _to_provider_instrument(row)
                if item.market in wanted:
                    out.append(item)
        logger.info("Longbridge instruments fetched: %s", len(out))
        return out

    def _fetch_market(self, market: str) -> list[SecurityRow]:
        if self._list_fetcher is not None:
            return self._list_fetcher(market)
        return _fetch_security_list_live(market)


def _to_provider_instrument(row: SecurityRow) -> ProviderInstrument:
    market, region_hint, bare = parse_longbridge_symbol(row.symbol)
    exchange = map_longbridge_exchange(row.exchange, region_hint=region_hint)
    name_cn = row.name_cn.strip() or row.name_en.strip() or bare
    name_en = row.name_en.strip()
    currency = row.currency.strip().upper() or currency_for_market(market)
    return ProviderInstrument(
        provider=PROVIDER_NAME,
        provider_symbol=row.symbol.strip().upper(),
        provider_exchange=exchange,
        name_cn=name_cn,
        name_en=name_en,
        market=market,
        exchange=exchange,
        currency=currency,
        asset_type=AssetType.EQUITY.value,
        status=InstrumentStatus.ACTIVE.value,
        symbol=bare,
    )


def _fetch_security_list_live(market: str) -> list[SecurityRow]:
    """Call Longbridge ``security_list`` + batched ``static_info``."""
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
    base: dict[str, SecurityRow] = {}
    for sec in securities:
        sym = str(sec.symbol).strip()
        if not sym:
            continue
        name_cn = str(sec.name_cn).strip()
        name_en = str(sec.name_en).strip()
        if not name_en:
            name_en = str(sec.name_hk).strip()
        base[sym.upper()] = SecurityRow(
            symbol=sym,
            name_cn=name_cn,
            name_en=name_en,
            exchange="",
            currency="",
        )

    symbols = list(base.keys())
    for i in range(0, len(symbols), _STATIC_INFO_BATCH):
        chunk = symbols[i : i + _STATIC_INFO_BATCH]
        try:
            infos = ctx.static_info(chunk)
        except Exception:
            logger.exception(
                "Longbridge static_info failed for %s symbols; keeping list names",
                len(chunk),
            )
            continue
        for info in infos:
            sym = str(info.symbol).strip().upper()
            if sym not in base:
                continue
            prev = base[sym]
            name_cn = str(info.name_cn).strip() or prev.name_cn
            name_en = str(info.name_en).strip() or prev.name_en
            exchange = str(info.exchange).strip()
            currency = str(info.currency).strip()
            base[sym] = SecurityRow(
                symbol=prev.symbol,
                name_cn=name_cn,
                name_en=name_en,
                exchange=exchange,
                currency=currency,
            )

    return list(base.values())


def _build_config() -> Config:
    """Build Longbridge Config from CatallaX settings or process env."""
    app_key = settings.longbridge_app_key.strip()
    app_secret = settings.longbridge_app_secret.strip()
    access_token = settings.longbridge_access_token.strip()
    if app_key and app_secret and access_token:
        return Config.from_apikey(app_key, app_secret, access_token)
    return Config.from_apikey_env()
