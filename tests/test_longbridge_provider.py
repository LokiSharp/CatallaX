"""Unit tests for Longbridge symbol parsing and provider mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING

from catallax.domain.enums import Market
from catallax.providers.base import ProviderInstrument
from catallax.providers.fallback import FallbackMarketDataProvider
from catallax.providers.longbridge.provider import LongbridgeMarketDataProvider
from catallax.providers.longbridge.symbols import (
    currency_for_market,
    parse_longbridge_symbol,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def test_parse_longbridge_symbol() -> None:
    assert parse_longbridge_symbol("AAPL.US") == ("US", "US", "AAPL")
    assert parse_longbridge_symbol("BRK.B.US") == ("US", "US", "BRK.B")
    assert parse_longbridge_symbol("BRK.A.US") == ("US", "US", "BRK.A")
    assert parse_longbridge_symbol("600519.SH") == ("CN", "SSE", "600519")
    assert parse_longbridge_symbol("000001.SZ") == ("CN", "SZSE", "000001")
    assert parse_longbridge_symbol("700.HK") == ("HK", "SEHK", "700")


def test_currency_for_market() -> None:
    assert currency_for_market("US") == "USD"
    assert currency_for_market("CN") == "CNY"
    assert currency_for_market("HK") == "HKD"


def test_longbridge_provider_from_injected_list() -> None:
    def fetch(market: str) -> list[tuple[str, str]]:
        if market == "US":
            return [("AAPL.US", "Apple"), ("BRK.B.US", "Berkshire B")]
        if market == "CN":
            return [("600519.SH", "贵州茅台")]
        return []

    provider = LongbridgeMarketDataProvider(list_fetcher=fetch)
    rows = provider.get_instruments(markets=["CN", "US"])
    assert len(rows) == 3
    symbols = {r.symbol for r in rows}
    assert symbols == {"AAPL", "BRK.B", "600519"}
    brk = next(r for r in rows if r.symbol == "BRK.B")
    assert brk.provider_symbol == "BRK.B.US"
    assert brk.market == Market.US.value
    assert brk.provider == "longbridge"
    moutai = next(r for r in rows if r.symbol == "600519")
    assert moutai.exchange == "SSE"
    assert moutai.currency == "CNY"


def test_fallback_uses_secondary_on_primary_failure() -> None:
    class Boom:
        @property
        def name(self) -> str:
            return "primary"

        def get_instruments(
            self,
            *,
            markets: Sequence[str] | None = None,
        ) -> list[ProviderInstrument]:
            _ = markets
            msg = "network down"
            raise RuntimeError(msg)

    class Ok:
        @property
        def name(self) -> str:
            return "secondary"

        def get_instruments(
            self,
            *,
            markets: Sequence[str] | None = None,
        ) -> list[ProviderInstrument]:
            _ = markets
            return [
                ProviderInstrument(
                    provider="secondary",
                    provider_symbol="AAPL",
                    provider_exchange="",
                    name="Apple",
                    market="US",
                    exchange="US",
                    currency="USD",
                    asset_type="equity",
                    symbol="AAPL",
                )
            ]

    fb = FallbackMarketDataProvider(Boom(), Ok())  # type: ignore[arg-type]
    items = fb.get_instruments(markets=["US"])
    assert len(items) == 1
    assert fb.name == "secondary"


def test_fallback_uses_secondary_on_empty_primary() -> None:
    class Empty:
        @property
        def name(self) -> str:
            return "primary"

        def get_instruments(
            self,
            *,
            markets: Sequence[str] | None = None,
        ) -> list[ProviderInstrument]:
            _ = markets
            return []

    class Ok:
        @property
        def name(self) -> str:
            return "secondary"

        def get_instruments(
            self,
            *,
            markets: Sequence[str] | None = None,
        ) -> list[ProviderInstrument]:
            _ = markets
            return [
                ProviderInstrument(
                    provider="secondary",
                    provider_symbol="MSFT",
                    provider_exchange="",
                    name="Microsoft",
                    market="US",
                    exchange="US",
                    currency="USD",
                    asset_type="equity",
                    symbol="MSFT",
                )
            ]

    fb = FallbackMarketDataProvider(Empty(), Ok())  # type: ignore[arg-type]
    items = fb.get_instruments()
    assert items[0].symbol == "MSFT"
    assert fb.name == "secondary"
