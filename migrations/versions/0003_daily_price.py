"""Daily price table for OHLCV bars.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08

Milestone 1.2 — schema + repository only; no market-data providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create daily_price with natural-key primary key and day indexes."""
    op.create_table(
        "daily_price",
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("high", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("low", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("close", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("volume", sa.Numeric(precision=24, scale=4), nullable=False),
        sa.Column("amount", sa.Numeric(precision=24, scale=4), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instrument.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("instrument_id", "trade_date"),
    )
    op.create_index(
        "ix_daily_price_trade_date",
        "daily_price",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        "ix_daily_price_trade_date_instrument",
        "daily_price",
        ["trade_date", "instrument_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop daily_price."""
    op.drop_index(
        "ix_daily_price_trade_date_instrument",
        table_name="daily_price",
    )
    op.drop_index("ix_daily_price_trade_date", table_name="daily_price")
    op.drop_table("daily_price")
