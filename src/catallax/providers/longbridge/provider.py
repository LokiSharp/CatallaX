"""Longbridge OpenAPI market-data provider (instruments + daily bars)."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from longbridge.openapi import (
    AdjustType,
    Config,
    Market,
    Period,
    QuoteContext,
    Security,
    TradeSessions,
)

from catallax.config import settings
from catallax.domain.markets import DEFAULT_MARKETS
from catallax.progress import ProgressLine
from catallax.providers.base import ProviderDailyBar, ProviderInstrument
from catallax.providers.longbridge.bars import (
    DAILY_BAR_SOURCE,
    candlestick_to_bar_fields,
    iter_date_windows,
)
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
    name_hk: str
    exchange: str
    currency: str


ListFetcher = Callable[[str], list[SecurityRow]]
BarsFetcher = Callable[[str, date, date], list[ProviderDailyBar]]


class LongbridgeMarketDataProvider:
    """Longbridge OpenAPI: security lists + daily history bars.

    Instruments: ``security_list`` + batched ``static_info``.
    Daily bars: ``history_candlesticks_by_date`` with ForwardAdjust / Intraday.
    """

    def __init__(
        self,
        *,
        list_fetcher: ListFetcher | None = None,
        bars_fetcher: BarsFetcher | None = None,
    ) -> None:
        self._list_fetcher = list_fetcher
        self._bars_fetcher = bars_fetcher

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        wanted = {m.upper() for m in markets} if markets else set(DEFAULT_MARKETS)
        lb_markets = [m for m in ("CN", "HK", "US") if m in wanted]

        out: list[ProviderInstrument] = []
        progress = ProgressLine()
        markets_label = ",".join(lb_markets) if lb_markets else ",".join(sorted(wanted))
        progress.update(f"fetch {markets_label} …")
        for lb_market in lb_markets:
            rows = self._fetch_market(lb_market, progress=progress)
            for row in rows:
                item = _to_provider_instrument(row)
                if item.market in wanted:
                    out.append(item)
        progress.finish(f"fetched {len(out)} instruments ({markets_label})")
        return out

    def get_daily_bars(
        self,
        *,
        provider_symbol: str,
        start: date,
        end: date,
    ) -> list[ProviderDailyBar]:
        """Daily OHLCV for one Longbridge symbol over ``[start, end]`` inclusive."""
        if end < start:
            msg = f"end {end} is before start {start}"
            raise ValueError(msg)
        sym = provider_symbol.strip().upper()
        if self._bars_fetcher is not None:
            return self._bars_fetcher(sym, start, end)
        return _fetch_daily_bars_live(sym, start, end)

    def _fetch_market(
        self,
        market: str,
        *,
        progress: ProgressLine | None = None,
    ) -> list[SecurityRow]:
        if self._list_fetcher is not None:
            return self._list_fetcher(market)
        return _fetch_security_list_live(market, progress=progress)


def _fetch_daily_bars_live(
    provider_symbol: str,
    start: date,
    end: date,
) -> list[ProviderDailyBar]:
    """Call Longbridge history candlesticks (windowed) and map to DTOs."""
    config = _build_config()
    ctx = QuoteContext(config)
    by_date: dict[date, ProviderDailyBar] = {}
    for win_start, win_end in iter_date_windows(start, end):
        candles = ctx.history_candlesticks_by_date(
            provider_symbol,
            Period.Day,
            AdjustType.ForwardAdjust,
            win_start,
            win_end,
            TradeSessions.Intraday,
        )
        for candle in candles:
            trade_date, o, h, low, c, vol, amount = candlestick_to_bar_fields(
                candle,
                provider_symbol=provider_symbol,
            )
            if trade_date < start or trade_date > end:
                continue
            by_date[trade_date] = ProviderDailyBar(
                provider_symbol=provider_symbol,
                trade_date=trade_date,
                open=o,
                high=h,
                low=low,
                close=c,
                volume=vol,
                amount=amount,
                source=DAILY_BAR_SOURCE,
            )
    return [by_date[d] for d in sorted(by_date)]


def _to_provider_instrument(row: SecurityRow) -> ProviderInstrument:
    market, region_hint, bare = parse_longbridge_symbol(row.symbol)
    exchange = map_longbridge_exchange(row.exchange, region_hint=region_hint)
    name_cn = row.name_cn.strip() or row.name_en.strip() or row.name_hk.strip() or bare
    name_en = row.name_en.strip()
    name_hk = row.name_hk.strip()
    currency = row.currency.strip().upper() or currency_for_market(market)
    return ProviderInstrument(
        provider=PROVIDER_NAME,
        provider_symbol=row.symbol.strip().upper(),
        provider_exchange=exchange,
        market=market,
        exchange=exchange,
        name_cn=name_cn,
        name_en=name_en,
        name_hk=name_hk,
        currency=currency,
        symbol=bare,
    )


def _fetch_security_list_live(
    market: str,
    *,
    progress: ProgressLine | None = None,
) -> list[SecurityRow]:
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

    if progress is not None:
        progress.update(f"fetch {market}: security_list …")
    securities = ctx.security_list(market_enum)
    base = _rows_from_security_list(securities)
    _enrich_with_static_info(ctx, base, market=market, progress=progress)
    return list(base.values())


def _rows_from_security_list(securities: Sequence[Security]) -> dict[str, SecurityRow]:
    """Build symbol → row map from ``security_list`` results."""
    base: dict[str, SecurityRow] = {}
    for sec in securities:
        sym = str(sec.symbol).strip()
        if not sym:
            continue
        base[sym.upper()] = SecurityRow(
            symbol=sym,
            name_cn=str(sec.name_cn).strip(),
            name_en=str(sec.name_en).strip(),
            name_hk=str(sec.name_hk).strip(),
            exchange="",
            currency="",
        )
    return base


def _enrich_with_static_info(
    ctx: QuoteContext,
    base: dict[str, SecurityRow],
    *,
    market: str,
    progress: ProgressLine | None = None,
) -> None:
    """Mutate ``base`` with batched ``static_info`` exchange / currency / names."""
    symbols = list(base.keys())
    if not symbols:
        return
    total_batches = (len(symbols) + _STATIC_INFO_BATCH - 1) // _STATIC_INFO_BATCH
    for batch_idx, i in enumerate(range(0, len(symbols), _STATIC_INFO_BATCH), start=1):
        chunk = symbols[i : i + _STATIC_INFO_BATCH]
        if progress is not None:
            progress.update(
                f"fetch {market}: static_info {batch_idx}/{total_batches} "
                f"({len(symbols)} symbols)",
            )
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
            base[sym] = SecurityRow(
                symbol=prev.symbol,
                name_cn=str(info.name_cn).strip() or prev.name_cn,
                name_en=str(info.name_en).strip() or prev.name_en,
                name_hk=str(info.name_hk).strip() or prev.name_hk,
                exchange=str(info.exchange).strip(),
                currency=str(info.currency).strip(),
            )


def _build_config() -> Config:
    """Build Longbridge Config from CatallaX settings or process env."""
    app_key = settings.longbridge_app_key.strip()
    app_secret = settings.longbridge_app_secret.strip()
    access_token = settings.longbridge_access_token.strip()
    if app_key and app_secret and access_token:
        return Config.from_apikey(
            app_key,
            app_secret,
            access_token,
            # Avoid printing the quote-package table over our progress line.
            enable_print_quote_packages=False,
        )
    # from_apikey_env only reads LONGBRIDGE_PRINT_QUOTE_PACKAGES from the env.
    os.environ.setdefault("LONGBRIDGE_PRINT_QUOTE_PACKAGES", "false")
    return Config.from_apikey_env()
