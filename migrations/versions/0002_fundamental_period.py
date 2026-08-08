"""Add fundamental_period for PIT-ready EPS/BPS history.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09

Stores per-share metrics by fiscal period end. announcement_date and
available_date are nullable when the provider does not supply them
(Longbridge financial_report currently does not).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create fundamental_period table."""
    op.create_table(
        "fundamental_period",
        sa.Column("instrument_id", sa.BigInteger(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_label", sa.String(length=32), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("eps", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("bps", sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("announcement_date", sa.Date(), nullable=True),
        sa.Column("available_date", sa.Date(), nullable=True),
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
        sa.PrimaryKeyConstraint(
            "instrument_id",
            "period_end",
            "source",
            name="pk_fundamental_period",
        ),
    )
    op.create_index(
        "ix_fundamental_period_period_end",
        "fundamental_period",
        ["period_end"],
        unique=False,
    )
    op.create_index(
        "ix_fundamental_period_available",
        "fundamental_period",
        ["instrument_id", "available_date"],
        unique=False,
    )


def downgrade() -> None:
    """Drop fundamental_period."""
    op.drop_index(
        "ix_fundamental_period_available",
        table_name="fundamental_period",
    )
    op.drop_index(
        "ix_fundamental_period_period_end",
        table_name="fundamental_period",
    )
    op.drop_table("fundamental_period")
