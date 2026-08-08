"""Instrument bilingual names + stable unique key (market, symbol).

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-09

- Add name_en; treat existing name as Chinese/local name (name stays).
- Unique key becomes (market, symbol) so exchange can be corrected without
  creating duplicate instruments (e.g. US/US/AAPL → US/NASDAQ/AAPL).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add name_en and switch uniqueness to (market, symbol)."""
    op.add_column(
        "instrument",
        sa.Column(
            "name_en",
            sa.String(length=256),
            server_default=sa.text("''"),
            nullable=False,
        ),
    )
    # Drop old unique that included exchange.
    op.drop_constraint(
        "uq_instrument_market_exchange_symbol",
        "instrument",
        type_="unique",
    )
    # If bad historical rows already duplicated by (market, symbol) with
    # different exchange, keep the lowest id and drop the rest.
    op.execute(
        sa.text(
            """
            DELETE FROM instrument a
            USING instrument b
            WHERE a.market = b.market
              AND a.symbol = b.symbol
              AND a.id > b.id
            """
        )
    )
    op.create_unique_constraint(
        "uq_instrument_market_symbol",
        "instrument",
        ["market", "symbol"],
    )
    # Index exchange alone for filters; not part of identity.
    op.create_index("ix_instrument_exchange", "instrument", ["exchange"], unique=False)


def downgrade() -> None:
    """Restore previous unique key and drop name_en."""
    op.drop_index("ix_instrument_exchange", table_name="instrument")
    op.drop_constraint("uq_instrument_market_symbol", "instrument", type_="unique")
    op.create_unique_constraint(
        "uq_instrument_market_exchange_symbol",
        "instrument",
        ["market", "exchange", "symbol"],
    )
    op.drop_column("instrument", "name_en")
