"""AKShare implementation of MarketDataProvider (instruments only for M1.3)."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Sequence
from typing import Any, cast

import akshare as ak
import pandas as pd

from catallax.domain.enums import AssetType, InstrumentStatus, Market
from catallax.providers.base import ProviderInstrument

logger = logging.getLogger(__name__)

PROVIDER_NAME = "akshare"

AkFetch = Callable[[], pd.DataFrame]


def infer_cn_exchange(code: str) -> tuple[str, str]:
    """Map A-share code to (CatallaX exchange, provider exchange token)."""
    c = code.strip()
    if c.startswith(("60", "68", "90")):
        return "SSE", "SH"
    if c.startswith(("00", "30", "20")):
        return "SZSE", "SZ"
    if c.startswith(("8", "4")):
        return "BSE", "BJ"
    return "UNKNOWN", ""


def clean_name(raw: str) -> str:
    """Collapse internal whitespace in Chinese names (e.g. '万  科Ａ')."""
    return re.sub(r"\s+", "", raw.strip())


def normalize_us_symbol(raw: str) -> str:
    """Normalize US tickers from AKShare / East-money list formats.

    East-money ``stock_us_spot_em`` builds codes as ``{market_id}.{ticker}``
    (e.g. ``105.AAPL``, ``106.BRK.B``). Only strip a **numeric** market-id
    prefix. Do **not** treat class-share dots as separators — otherwise
    ``BRK.B`` collapses to ``B``.
    """
    text = raw.strip().upper()
    if "." not in text:
        return text
    head, rest = text.split(".", maxsplit=1)
    if head.isdigit() and rest:
        return rest
    return text


def _cell_str(value: object) -> str:
    """Coerce a pandas cell to a plain string."""
    return str(value).strip()


class AkshareMarketDataProvider:
    """Fetch security lists from AKShare. No strategy code should import this."""

    def __init__(
        self,
        *,
        fetch_cn: AkFetch | None = None,
        fetch_us: AkFetch | None = None,
    ) -> None:
        self._fetch_cn = fetch_cn
        self._fetch_us = fetch_us

    @property
    def name(self) -> str:
        return PROVIDER_NAME

    def get_instruments(
        self,
        *,
        markets: Sequence[str] | None = None,
    ) -> list[ProviderInstrument]:
        if markets:
            wanted = {m.upper() for m in markets}
        else:
            wanted = {Market.CN.value, Market.US.value}
        rows: list[ProviderInstrument] = []
        if Market.CN.value in wanted:
            rows.extend(self._get_cn_instruments())
        if Market.US.value in wanted:
            rows.extend(self._get_us_instruments())
        return rows

    def _get_cn_instruments(self) -> list[ProviderInstrument]:
        df = self._load_cn_frame()
        if df.empty:
            return []

        code_col = _first_col(df, ("code", "证券代码", "代码"))
        name_col = _first_col(df, ("name", "证券简称", "名称"))
        out: list[ProviderInstrument] = []
        for record in _as_records(df):
            code = _cell_str(record[code_col]).zfill(6)
            name = clean_name(_cell_str(record[name_col]))
            if not code or code.lower() == "nan":
                continue
            exchange, provider_exchange = infer_cn_exchange(code)
            out.append(
                ProviderInstrument(
                    provider=PROVIDER_NAME,
                    provider_symbol=code,
                    provider_exchange=provider_exchange,
                    name=name or code,
                    name_en="",
                    market=Market.CN.value,
                    exchange=exchange,
                    currency="CNY",
                    asset_type=AssetType.EQUITY.value,
                    status=InstrumentStatus.ACTIVE.value,
                    symbol=code,
                )
            )
        logger.info("AKShare CN instruments fetched: %s", len(out))
        return out

    def _get_us_instruments(self) -> list[ProviderInstrument]:
        df = self._load_us_frame()
        if df.empty:
            return []

        code_col = _first_col(
            df,
            ("代码", "symbol", "code", "股票代码", "美股代码"),
        )
        name_col = _first_col(
            df,
            ("名称", "name", "股票名称", "美股名称"),
        )
        out: list[ProviderInstrument] = []
        seen: set[str] = set()
        for record in _as_records(df):
            raw_code = _cell_str(record[code_col])
            if not raw_code or raw_code.lower() == "nan":
                continue
            symbol = normalize_us_symbol(raw_code)
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            name_raw = _cell_str(record[name_col]) if name_col else symbol
            name = name_raw if name_raw.lower() != "nan" else symbol
            out.append(
                ProviderInstrument(
                    provider=PROVIDER_NAME,
                    provider_symbol=symbol,
                    provider_exchange="",
                    name=name or symbol,
                    name_en=name or symbol,
                    market=Market.US.value,
                    # AKShare list endpoints omit venue; do not fake "US" as exchange.
                    exchange="UNKNOWN",
                    currency="USD",
                    asset_type=AssetType.EQUITY.value,
                    status=InstrumentStatus.ACTIVE.value,
                    symbol=symbol,
                )
            )
        logger.info("AKShare US instruments fetched: %s", len(out))
        return out

    def _load_cn_frame(self) -> pd.DataFrame:
        if self._fetch_cn is not None:
            return self._fetch_cn()
        return ak.stock_info_a_code_name()

    def _load_us_frame(self) -> pd.DataFrame:
        if self._fetch_us is not None:
            return self._fetch_us()
        try:
            return ak.stock_us_spot_em()
        except Exception:
            logger.warning(
                "stock_us_spot_em failed; falling back to get_us_stock_name",
                exc_info=True,
            )
            return ak.get_us_stock_name()


def _first_col(df: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in df.columns:
            return name
    msg = f"None of columns {candidates} found in {list(df.columns)}"
    raise KeyError(msg)


def _as_records(df: pd.DataFrame) -> list[dict[str, object]]:
    """Convert a DataFrame to plain dict rows for strict typing."""
    # pandas stubs leave DataFrame methods partially unknown under strict mode.
    frame: Any = df
    raw: Any = frame.to_dict(orient="records")
    return cast("list[dict[str, object]]", raw)
