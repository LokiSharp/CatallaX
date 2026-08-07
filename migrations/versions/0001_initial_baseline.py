"""Initial empty schema baseline.

Revision ID: 0001
Revises:
Create Date: 2026-08-07

Establishes the Alembic revision chain before any real tables exist.
Future schema changes should revise this baseline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: schema is empty at Milestone 0."""


def downgrade() -> None:
    """No-op: nothing to drop from the empty baseline."""
