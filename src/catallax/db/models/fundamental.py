"""Fiscal-period fundamentals (EPS/BPS) with optional PIT dates."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — SQLAlchemy Mapped eval
from decimal import Decimal  # noqa: TC003 — SQLAlchemy Mapped eval

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from catallax.db.base import Base


class FundamentalPeriod(Base):
    """One fiscal period's per-share metrics for an instrument.

    ``announcement_date`` / ``available_date`` may be NULL when the upstream
    feed does not provide them. PIT-safe PE/PB must only use rows where
    ``available_date`` is set and ``available_date <= as_of_date``.
    """

    __tablename__ = "fundamental_period"
    __table_args__ = (
        PrimaryKeyConstraint(
            "instrument_id",
            "period_end",
            "source",
            name="pk_fundamental_period",
        ),
        Index("ix_fundamental_period_period_end", "period_end"),
        Index(
            "ix_fundamental_period_available",
            "instrument_id",
            "available_date",
        ),
    )

    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instrument.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    period_label: Mapped[str] = mapped_column(String(32), nullable=False)
    fiscal_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    bps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    available_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
