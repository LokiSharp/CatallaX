"""Initial schema (squashed for early development).

Revision ID: 0001
Revises:
Create Date: 2026-08-09

Single baseline for current CatallaX tables:
instrument, instrument_symbol_map, data_sync_log, daily_price.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create full schema at current design."""
    op.create_table(
        "instrument",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("name_cn", sa.String(length=256), nullable=False),
        sa.Column(
            "name_en",
            sa.String(length=256),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "name_hk",
            sa.String(length=256),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column("market", sa.String(length=8), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("list_date", sa.Date(), nullable=True),
        sa.Column("delist_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market", "symbol", name="uq_instrument_market_symbol"),
    )
    op.create_index(
        "ix_instrument_market_status",
        "instrument",
        ["market", "status"],
        unique=False,
    )
    op.create_index(
        "ix_instrument_list_delist",
        "instrument",
        ["list_date", "delist_date"],
        unique=False,
    )
    op.create_index("ix_instrument_exchange", "instrument", ["exchange"], unique=False)

    op.create_table(
        "instrument_symbol_map",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column(
            "provider_exchange",
            sa.String(length=32),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_symbol",
            "provider_exchange",
            name="uq_symbol_map_provider_symbol_exchange",
        ),
    )
    op.create_index(
        "ix_symbol_map_instrument_id",
        "instrument_symbol_map",
        ["instrument_id"],
        unique=False,
    )
    op.create_index(
        "ix_symbol_map_provider_active",
        "instrument_symbol_map",
        ["provider", "is_active"],
        unique=False,
    )

    op.create_table(
        "data_sync_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("entity", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_written", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_sync_log_provider_entity_started",
        "data_sync_log",
        ["provider", "entity", "started_at"],
        unique=False,
    )

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
    """Drop all tables from the baseline schema."""
    op.drop_index(
        "ix_daily_price_trade_date_instrument",
        table_name="daily_price",
    )
    op.drop_index("ix_daily_price_trade_date", table_name="daily_price")
    op.drop_table("daily_price")
    op.drop_index(
        "ix_data_sync_log_provider_entity_started",
        table_name="data_sync_log",
    )
    op.drop_table("data_sync_log")
    op.drop_index("ix_symbol_map_provider_active", table_name="instrument_symbol_map")
    op.drop_index("ix_symbol_map_instrument_id", table_name="instrument_symbol_map")
    op.drop_table("instrument_symbol_map")
    op.drop_index("ix_instrument_exchange", table_name="instrument")
    op.drop_index("ix_instrument_list_delist", table_name="instrument")
    op.drop_index("ix_instrument_market_status", table_name="instrument")
    op.drop_table("instrument")
