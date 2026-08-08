"""Thin read API for daily prices from PostgreSQL.

Strategies and research code should prefer this service over repositories so
they never depend on SQLAlchemy query details or provider symbols as keys.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from catallax.db.repositories.daily_price import DailyPriceRepository
from catallax.db.repositories.instrument import InstrumentRepository

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from catallax.db.models.daily_price import DailyPrice


@dataclass(frozen=True, slots=True)
class PriceBar:
    """One daily OHLCV bar resolved for an internal instrument_id."""

    instrument_id: int
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None
    source: str


def _to_bar(row: DailyPrice) -> PriceBar:
    return PriceBar(
        instrument_id=row.instrument_id,
        trade_date=row.trade_date,
        open=row.open,
        high=row.high,
        low=row.low,
        close=row.close,
        volume=row.volume,
        amount=row.amount,
        source=row.source,
    )


class PriceQueryService:
    """Read-only daily price queries against PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._prices = DailyPriceRepository(session)
        self._instruments = InstrumentRepository(session)

    def get_prices(
        self,
        *,
        instrument_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PriceBar]:
        """Return bars for ``instrument_id`` ordered by ``trade_date`` ascending.

        Does not call external providers. Empty list if no rows in range.
        """
        rows = self._prices.list_by_instrument(
            instrument_id,
            start=start_date,
            end=end_date,
        )
        return [_to_bar(r) for r in rows]

    def get_prices_by_symbol(
        self,
        *,
        market: str,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PriceBar]:
        """Resolve ``(market, symbol)`` → ``instrument_id``, then load bars.

        Raises:
            LookupError: if no instrument exists for the business key.
        """
        instrument = self._instruments.get_by_business_key(
            market=market.upper(),
            symbol=symbol.strip().upper(),
        )
        if instrument is None:
            msg = f"instrument not found for market={market!r} symbol={symbol!r}"
            raise LookupError(msg)
        return self.get_prices(
            instrument_id=instrument.id,
            start_date=start_date,
            end_date=end_date,
        )
