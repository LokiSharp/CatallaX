"""Daily OHLCV bars keyed by instrument_id + trade_date."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — required by SQLAlchemy Mapped eval
from decimal import Decimal  # noqa: TC003 — required by SQLAlchemy Mapped eval
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from catallax.db.base import Base

if TYPE_CHECKING:
    from catallax.db.models.instrument import Instrument


class DailyPrice(Base):
    """One trading-day bar for one instrument.

    Primary key is the natural key ``(instrument_id, trade_date)`` so
    re-syncs cannot create duplicate bars for the same day.
    """

    __tablename__ = "daily_price"
    __table_args__ = (
        # PK already supports "single stock history" ordered by trade_date.
        # Extra index supports "all bars on a calendar day" (full-market scan).
        Index("ix_daily_price_trade_date", "trade_date"),
        Index("ix_daily_price_trade_date_instrument", "trade_date", "instrument_id"),
    )

    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instrument.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 4), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    instrument: Mapped[Instrument] = relationship("Instrument")
