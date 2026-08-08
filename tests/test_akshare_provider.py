"""Unit tests for AKShare instrument mapping (no live network)."""

from __future__ import annotations

import pandas as pd

from catallax.domain.enums import Market
from catallax.providers.akshare.provider import (
    AkshareMarketDataProvider,
    infer_cn_exchange,
    normalize_us_symbol,
)


def test_infer_cn_exchange() -> None:
    assert infer_cn_exchange("600519") == ("SSE", "SH")
    assert infer_cn_exchange("000001") == ("SZSE", "SZ")
    assert infer_cn_exchange("300750") == ("SZSE", "SZ")
    assert infer_cn_exchange("688001") == ("SSE", "SH")
    assert infer_cn_exchange("830799")[0] == "BSE"


def test_normalize_us_symbol() -> None:
    assert normalize_us_symbol("AAPL") == "AAPL"
    assert normalize_us_symbol("105.AAPL") == "AAPL"
    assert normalize_us_symbol("aapl") == "AAPL"
    # Class shares must keep the suffix (not collapse to "A"/"B").
    assert normalize_us_symbol("BRK.A") == "BRK.A"
    assert normalize_us_symbol("BRK.B") == "BRK.B"
    assert normalize_us_symbol("106.BRK.B") == "BRK.B"
    assert normalize_us_symbol("BF.B") == "BF.B"


def test_get_instruments_from_injected_frames() -> None:
    cn = pd.DataFrame(
        {
            "code": ["600519", "000001"],
            "name": ["贵州茅台", "平 安银行"],
        }
    )
    us = pd.DataFrame(
        {
            "代码": ["105.AAPL", "MSFT", "106.BRK.B", "BRK.A"],
            "名称": ["苹果", "微软", "伯克希尔B", "伯克希尔A"],
        }
    )
    hk = pd.DataFrame(
        {
            "代码": ["00700", "00941"],
            "名称": ["腾讯控股", "中国移动"],
        }
    )
    provider = AkshareMarketDataProvider(
        fetch_cn=lambda: cn,
        fetch_us=lambda: us,
        fetch_hk=lambda: hk,
    )
    rows = provider.get_instruments(markets=["CN", "US", "HK"])
    assert len(rows) == 8

    cn_rows = [r for r in rows if r.market == Market.CN.value]
    assert {r.provider_symbol for r in cn_rows} == {"600519", "000001"}
    moutai = next(r for r in cn_rows if r.provider_symbol == "600519")
    assert moutai.exchange == "SSE"
    assert moutai.provider_exchange == "SH"
    assert moutai.currency == "CNY"
    assert moutai.provider == "akshare"

    us_rows = [r for r in rows if r.market == Market.US.value]
    symbols = {r.symbol for r in us_rows}
    assert symbols == {"AAPL", "MSFT", "BRK.B", "BRK.A"}
    aapl = next(r for r in us_rows if r.symbol == "AAPL")
    assert aapl.provider_symbol == "AAPL"
    assert aapl.currency == "USD"
    brk_b = next(r for r in us_rows if r.symbol == "BRK.B")
    assert brk_b.provider_symbol == "BRK.B"

    hk_rows = [r for r in rows if r.market == Market.HK.value]
    assert {r.symbol for r in hk_rows} == {"700", "941"}
    tencent = next(r for r in hk_rows if r.symbol == "700")
    assert tencent.exchange == "SEHK"
    assert tencent.currency == "HKD"
    assert tencent.name_cn == "腾讯控股"
