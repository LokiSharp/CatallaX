"""Parse Longbridge ``ticker.region`` symbols into CatallaX fields."""

from __future__ import annotations


def parse_longbridge_symbol(symbol: str) -> tuple[str, str, str]:
    """Split a Longbridge symbol into ``(market, exchange, bare_symbol)``.

    Examples:
        ``AAPL.US`` → ``(US, US, AAPL)``
        ``BRK.B.US`` → ``(US, US, BRK.B)``  (class share kept)
        ``600519.SH`` → ``(CN, SSE, 600519)``
        ``000001.SZ`` → ``(CN, SZSE, 000001)``
        ``700.HK`` → ``(HK, SEHK, 700)``
    """
    text = symbol.strip().upper()
    if "." not in text:
        return "US", "US", text

    bare, region = text.rsplit(".", maxsplit=1)
    region_map: dict[str, tuple[str, str]] = {
        "US": ("US", "US"),
        "HK": ("HK", "SEHK"),
        "SH": ("CN", "SSE"),
        "SZ": ("CN", "SZSE"),
        "SG": ("SG", "SGX"),
    }
    if region in region_map and bare:
        market, exchange = region_map[region]
        return market, exchange, bare
    return "UNKNOWN", "UNKNOWN", text


def currency_for_market(market: str) -> str:
    """Default trading currency for a CatallaX market code."""
    return {
        "US": "USD",
        "CN": "CNY",
        "HK": "HKD",
        "SG": "SGD",
    }.get(market.upper(), "USD")
