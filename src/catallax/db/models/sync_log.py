"""Data sync job audit log."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — required by SQLAlchemy Mapped eval

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from catallax.db.base import Base


class DataSyncLog(Base):
    """Records each data synchronization attempt for observability and idempotency."""

    __tablename__ = "data_sync_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    entity: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'running'"),
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    records_written: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
