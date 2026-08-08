"""CRUD / upsert for daily_price."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from catallax.db.models.daily_price import DailyPrice
from catallax.db.models.instrument import Instrument

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session


class DailyPriceRepository:
    """Daily bar persistence. Callers own the Session transaction boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        instrument_id: int,
        trade_date: date,
        open_: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
        amount: Decimal | None = None,
        source: str,
    ) -> DailyPrice:
        """Insert a single bar (fails if the natural key already exists)."""
        row = DailyPrice(
            instrument_id=instrument_id,
            trade_date=trade_date,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            amount=amount,
            source=source,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get(
        self,
        *,
        instrument_id: int,
        trade_date: date,
    ) -> DailyPrice | None:
        """Fetch one bar by natural key."""
        return self._session.get(
            DailyPrice,
            {"instrument_id": instrument_id, "trade_date": trade_date},
        )

    def list_by_instrument(
        self,
        instrument_id: int,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[DailyPrice]:
        """Historical bars for one instrument, ascending by trade_date."""
        stmt = select(DailyPrice).where(DailyPrice.instrument_id == instrument_id)
        if start is not None:
            stmt = stmt.where(DailyPrice.trade_date >= start)
        if end is not None:
            stmt = stmt.where(DailyPrice.trade_date <= end)
        stmt = stmt.order_by(DailyPrice.trade_date.asc())
        return list(self._session.scalars(stmt).all())

    def list_by_trade_date(self, trade_date: date) -> list[DailyPrice]:
        """All bars on a calendar day (any market)."""
        stmt = (
            select(DailyPrice)
            .where(DailyPrice.trade_date == trade_date)
            .order_by(DailyPrice.instrument_id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_by_market_and_date(
        self,
        *,
        market: str,
        trade_date: date,
    ) -> list[DailyPrice]:
        """All bars for a market on a calendar day."""
        stmt = (
            select(DailyPrice)
            .join(Instrument, Instrument.id == DailyPrice.instrument_id)
            .where(
                Instrument.market == market,
                DailyPrice.trade_date == trade_date,
            )
            .order_by(DailyPrice.instrument_id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def upsert(
        self,
        *,
        instrument_id: int,
        trade_date: date,
        open_: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Decimal,
        amount: Decimal | None = None,
        source: str,
    ) -> DailyPrice:
        """Insert or update by (instrument_id, trade_date). Idempotent."""
        stmt = (
            insert(DailyPrice)
            .values(
                instrument_id=instrument_id,
                trade_date=trade_date,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=volume,
                amount=amount,
                source=source,
            )
            .on_conflict_do_update(
                index_elements=["instrument_id", "trade_date"],
                set_={
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                    "amount": amount,
                    "source": source,
                    "updated_at": func.now(),
                },
            )
            .returning(DailyPrice.instrument_id, DailyPrice.trade_date)
        )
        result = self._session.execute(stmt).one()
        self._session.expire_all()
        row = self.get(instrument_id=result.instrument_id, trade_date=result.trade_date)
        if row is None:  # pragma: no cover - defensive
            msg = (
                "upsert failed to load daily_price "
                f"instrument_id={result.instrument_id} trade_date={result.trade_date}"
            )
            raise RuntimeError(msg)
        return row
