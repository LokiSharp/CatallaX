"""CRUD for data_sync_log."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select

from catallax.db.models.sync_log import DataSyncLog
from catallax.domain.enums import SyncStatus

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class DataSyncLogRepository:
    """Sync job audit log persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def start(
        self,
        *,
        provider: str,
        entity: str,
        details: str | None = None,
    ) -> DataSyncLog:
        """Create a running sync log entry."""
        row = DataSyncLog(
            provider=provider,
            entity=entity,
            status=SyncStatus.RUNNING.value,
            details=details,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, log_id: int) -> DataSyncLog | None:
        """Fetch by primary key."""
        return self._session.get(DataSyncLog, log_id)

    def mark_success(
        self,
        log: DataSyncLog,
        *,
        records_written: int | None = None,
        details: str | None = None,
    ) -> DataSyncLog:
        """Mark a running log as successful."""
        log.status = SyncStatus.SUCCESS.value
        log.finished_at = datetime.now(UTC)
        log.records_written = records_written
        if details is not None:
            log.details = details
        self._session.flush()
        return log

    def mark_failed(
        self,
        log: DataSyncLog,
        *,
        error_message: str,
        details: str | None = None,
    ) -> DataSyncLog:
        """Mark a running log as failed."""
        log.status = SyncStatus.FAILED.value
        log.finished_at = datetime.now(UTC)
        log.error_message = error_message
        if details is not None:
            log.details = details
        self._session.flush()
        return log

    def get_latest(
        self,
        *,
        provider: str,
        entity: str,
    ) -> DataSyncLog | None:
        """Most recent log for a provider/entity pair."""
        stmt = (
            select(DataSyncLog)
            .where(
                DataSyncLog.provider == provider,
                DataSyncLog.entity == entity,
            )
            .order_by(DataSyncLog.started_at.desc(), DataSyncLog.id.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).one_or_none()
