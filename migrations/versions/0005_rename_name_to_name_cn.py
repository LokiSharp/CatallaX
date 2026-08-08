"""Rename instrument.name → instrument.name_cn.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-09
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Rename Chinese/local name column for explicit bilingual schema."""
    op.alter_column("instrument", "name", new_column_name="name_cn")


def downgrade() -> None:
    """Restore legacy column name."""
    op.alter_column("instrument", "name_cn", new_column_name="name")
