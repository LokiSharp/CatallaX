"""Local ledger of provider history-K queries (monthly symbol quota)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — required by SQLAlchemy Mapped eval

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from catallax.db.base import Base


class ProviderHistorySymbol(Base):
    """One provider symbol that requested history data in a calendar month.

    Longbridge counts unique symbols per natural month for history K-line
    quota. There is no official API to list them, so we record successful
    requests locally. Estimates may drift if other clients share the account.
    """

    __tablename__ = "provider_history_symbol"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_symbol",
            "year_month",
            name="uq_provider_history_symbol_month",
        ),
        Index("ix_provider_history_provider_month", "provider", "year_month"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    # UTC calendar month ``YYYY-MM``.
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    instrument_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("instrument.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    query_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )
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
