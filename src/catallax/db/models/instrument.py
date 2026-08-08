"""Security Master: instrument and provider symbol mapping."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003 — required by SQLAlchemy Mapped eval

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from catallax.db.base import Base


class Instrument(Base):
    """Canonical security identity used everywhere inside CatallaX."""

    __tablename__ = "instrument"
    __table_args__ = (
        UniqueConstraint(
            "market",
            "exchange",
            "symbol",
            name="uq_instrument_market_exchange_symbol",
        ),
        Index("ix_instrument_market_status", "market", "status"),
        Index("ix_instrument_list_delist", "list_date", "delist_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    market: Mapped[str] = mapped_column(String(8), nullable=False)
    exchange: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)
    list_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delist_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'active'"),
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

    symbol_maps: Mapped[list[InstrumentSymbolMap]] = relationship(
        back_populates="instrument",
        cascade="all, delete-orphan",
    )


class InstrumentSymbolMap(Base):
    """Maps a provider-specific symbol to an internal instrument_id."""

    __tablename__ = "instrument_symbol_map"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_symbol",
            "provider_exchange",
            name="uq_symbol_map_provider_symbol_exchange",
        ),
        Index("ix_symbol_map_instrument_id", "instrument_id"),
        Index("ix_symbol_map_provider_active", "provider", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("instrument.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(64), nullable=False)
    # Empty string when provider has no exchange dimension (avoids NULL unique issues).
    provider_exchange: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("''"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
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

    instrument: Mapped[Instrument] = relationship(back_populates="symbol_maps")
