"""Parse Longbridge ``ticker.region`` symbols and map exchange codes."""

from __future__ import annotations


def parse_longbridge_symbol(symbol: str) -> tuple[str, str, str]:
    """Split a Longbridge symbol into ``(market, region_hint, bare_symbol)``.

    ``region_hint`` is only a market region token (US/HK/SH/SZ), **not** a
    trading venue. Real exchange (NASDAQ/NYSE/SSE/...) comes from static_info.

    Examples:
        ``AAPL.US`` → ``(US, US, AAPL)``
        ``BRK.B.US`` → ``(US, US, BRK.B)``
        ``600519.SH`` → ``(CN, SH, 600519)``
        ``000001.SZ`` → ``(CN, SZ, 000001)``
        ``700.HK`` → ``(HK, HK, 700)``
    """
    text = symbol.strip().upper()
    if "." not in text:
        return "US", "US", text

    bare, region = text.rsplit(".", maxsplit=1)
    region_to_market: dict[str, str] = {
        "US": "US",
        "HK": "HK",
        "SH": "CN",
        "SZ": "CN",
        "SG": "SG",
    }
    if region in region_to_market and bare:
        return region_to_market[region], region, bare
    return "UNKNOWN", "UNKNOWN", text


def currency_for_market(market: str) -> str:
    """Default trading currency for a CatallaX market code."""
    return {
        "US": "USD",
        "CN": "CNY",
        "HK": "HKD",
        "SG": "SGD",
    }.get(market.upper(), "USD")


def map_longbridge_exchange(raw: str, *, region_hint: str = "") -> str:
    """Map Longbridge ``static_info.exchange`` to a CatallaX exchange code.

    Longbridge examples: ``NASD``, ``NYSE``, ``SEHK``, ``SHSE``, ``SZSE``.
    Region suffix alone (US) is **not** a valid exchange.
    """
    code = raw.strip().upper()
    mapping: dict[str, str] = {
        "NASD": "NASDAQ",
        "NASDAQ": "NASDAQ",
        "NYSE": "NYSE",
        "AMEX": "AMEX",
        "ARCA": "ARCA",
        "BATS": "BATS",
        "OTC": "OTC",
        "SEHK": "SEHK",
        "HKEX": "SEHK",
        "SHSE": "SSE",
        "SSE": "SSE",
        "SZSE": "SZSE",
        "BSE": "BSE",
        "SGX": "SGX",
    }
    if code in mapping:
        return mapping[code]
    if code:
        return code
    # Fallback from symbol region when static exchange missing.
    region_fallback: dict[str, str] = {
        "SH": "SSE",
        "SZ": "SZSE",
        "HK": "SEHK",
        "SG": "SGX",
        # Do not invent NASDAQ/NYSE from region US alone.
        "US": "UNKNOWN",
    }
    return region_fallback.get(region_hint.upper(), "UNKNOWN")
