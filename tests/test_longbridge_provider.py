"""Unit tests for Longbridge symbol parsing and provider mapping."""

from __future__ import annotations

from catallax.domain.enums import Market
from catallax.providers.longbridge.provider import (
    LongbridgeMarketDataProvider,
    SecurityRow,
)
from catallax.providers.longbridge.symbols import (
    currency_for_market,
    map_longbridge_exchange,
    parse_longbridge_symbol,
)


def test_parse_longbridge_symbol() -> None:
    assert parse_longbridge_symbol("AAPL.US") == ("US", "US", "AAPL")
    assert parse_longbridge_symbol("BRK.B.US") == ("US", "US", "BRK.B")
    assert parse_longbridge_symbol("BRK.A.US") == ("US", "US", "BRK.A")
    assert parse_longbridge_symbol("600519.SH") == ("CN", "SH", "600519")
    assert parse_longbridge_symbol("000001.SZ") == ("CN", "SZ", "000001")
    assert parse_longbridge_symbol("700.HK") == ("HK", "HK", "700")


def test_map_longbridge_exchange() -> None:
    assert map_longbridge_exchange("NASD") == "NASDAQ"
    assert map_longbridge_exchange("NYSE") == "NYSE"
    assert map_longbridge_exchange("SEHK") == "SEHK"
    assert map_longbridge_exchange("SHSE") == "SSE"
    assert map_longbridge_exchange("SZSE") == "SZSE"
    # Region alone is not a venue.
    assert map_longbridge_exchange("", region_hint="US") == "UNKNOWN"
    assert map_longbridge_exchange("", region_hint="SH") == "SSE"


def test_currency_for_market() -> None:
    assert currency_for_market("US") == "USD"
    assert currency_for_market("CN") == "CNY"
    assert currency_for_market("HK") == "HKD"


def test_longbridge_provider_from_injected_list() -> None:
    def fetch(market: str) -> list[SecurityRow]:
        if market == "US":
            return [
                SecurityRow("AAPL.US", "苹果", "Apple Inc.", "", "NASD", "USD"),
                SecurityRow("BRK.B.US", "伯克希尔B", "Berkshire B", "", "NYSE", "USD"),
            ]
        if market == "CN":
            return [
                SecurityRow(
                    "600519.SH",
                    "贵州茅台",
                    "Kweichow Moutai",
                    "",
                    "SHSE",
                    "CNY",
                ),
            ]
        if market == "HK":
            return [
                SecurityRow("700.HK", "腾讯控股", "TENCENT", "騰訊控股", "SEHK", "HKD"),
            ]
        return []

    provider = LongbridgeMarketDataProvider(list_fetcher=fetch)
    rows = provider.get_instruments(markets=["CN", "US", "HK"])
    assert len(rows) == 4

    aapl = next(r for r in rows if r.symbol == "AAPL")
    assert aapl.name_cn == "苹果"
    assert aapl.name_en == "Apple Inc."
    assert aapl.exchange == "NASDAQ"
    assert aapl.provider_symbol == "AAPL.US"

    brk = next(r for r in rows if r.symbol == "BRK.B")
    assert brk.exchange == "NYSE"
    assert brk.name_en == "Berkshire B"

    moutai = next(r for r in rows if r.symbol == "600519")
    assert moutai.exchange == "SSE"
    assert moutai.name_cn == "贵州茅台"
    assert moutai.name_en == "Kweichow Moutai"
    assert moutai.market == Market.CN.value

    tencent = next(r for r in rows if r.symbol == "700")
    assert tencent.market == Market.HK.value
    assert tencent.exchange == "SEHK"
    assert tencent.currency == "HKD"
    assert tencent.name_cn == "腾讯控股"
    assert tencent.name_en == "TENCENT"
    assert tencent.name_hk == "騰訊控股"
    assert tencent.provider_symbol == "700.HK"
