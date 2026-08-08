"""Rebuild instrument with logical column order (dev-stage).

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-09

Physical column order becomes:
id, symbol, name_cn, name_en, market, exchange, currency, asset_type,
list_date, delist_date, status, created_at, updated_at
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Recreate instrument so name_cn/name_en sit together after symbol."""
    op.execute(
        sa.text(
            "ALTER TABLE daily_price "
            "DROP CONSTRAINT IF EXISTS daily_price_instrument_id_fkey"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE instrument_symbol_map "
            "DROP CONSTRAINT IF EXISTS instrument_symbol_map_instrument_id_fkey"
        )
    )
    # Constraint names are schema-global; free the name before recreate.
    op.execute(
        sa.text(
            "ALTER TABLE instrument "
            "DROP CONSTRAINT IF EXISTS uq_instrument_market_symbol"
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS instrument_new"))

    op.create_table(
        "instrument_new",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("name_cn", sa.String(length=256), nullable=False),
        sa.Column(
            "name_en",
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

    op.execute(
        sa.text(
            """
            INSERT INTO instrument_new (
                id, symbol, name_cn, name_en, market, exchange, currency,
                asset_type, list_date, delist_date, status, created_at, updated_at
            )
            SELECT
                id, symbol, name_cn, name_en, market, exchange, currency,
                asset_type, list_date, delist_date, status, created_at, updated_at
            FROM instrument
            """
        )
    )

    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('instrument_new', 'id'),
                COALESCE((SELECT MAX(id) FROM instrument_new), 1),
                true
            )
            """
        )
    )

    op.drop_table("instrument")
    op.rename_table("instrument_new", "instrument")

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

    op.create_foreign_key(
        "daily_price_instrument_id_fkey",
        "daily_price",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_symbol_map_instrument_id_fkey",
        "instrument_symbol_map",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Rebuild previous physical order (name_en at end)."""
    op.execute(
        sa.text(
            "ALTER TABLE daily_price "
            "DROP CONSTRAINT IF EXISTS daily_price_instrument_id_fkey"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE instrument_symbol_map "
            "DROP CONSTRAINT IF EXISTS instrument_symbol_map_instrument_id_fkey"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE instrument "
            "DROP CONSTRAINT IF EXISTS uq_instrument_market_symbol"
        )
    )
    op.execute(sa.text("DROP TABLE IF EXISTS instrument_old"))

    op.create_table(
        "instrument_old",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("name_cn", sa.String(length=256), nullable=False),
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
        sa.Column(
            "name_en",
            sa.String(length=256),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("market", "symbol", name="uq_instrument_market_symbol"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO instrument_old (
                id, symbol, name_cn, market, exchange, currency, asset_type,
                list_date, delist_date, status, created_at, updated_at, name_en
            )
            SELECT
                id, symbol, name_cn, market, exchange, currency, asset_type,
                list_date, delist_date, status, created_at, updated_at, name_en
            FROM instrument
            """
        )
    )
    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('instrument_old', 'id'),
                COALESCE((SELECT MAX(id) FROM instrument_old), 1),
                true
            )
            """
        )
    )
    op.drop_table("instrument")
    op.rename_table("instrument_old", "instrument")
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
    op.create_foreign_key(
        "daily_price_instrument_id_fkey",
        "daily_price",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "instrument_symbol_map_instrument_id_fkey",
        "instrument_symbol_map",
        "instrument",
        ["instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
