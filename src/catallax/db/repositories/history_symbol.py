"""CRUD / upsert for provider_history_symbol quota ledger."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from catallax.db.models.history_symbol import ProviderHistorySymbol

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def utc_year_month(when: datetime | None = None) -> str:
    """Return ``YYYY-MM`` for ``when`` in UTC (default: now)."""
    ts = when if when is not None else datetime.now(UTC)
    ts = ts.replace(tzinfo=UTC) if ts.tzinfo is None else ts.astimezone(UTC)
    return f"{ts.year:04d}-{ts.month:02d}"


class ProviderHistorySymbolRepository:
    """Local history-query ledger. Callers own the Session transaction boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record_query(
        self,
        *,
        provider: str,
        provider_symbol: str,
        instrument_id: int | None = None,
        year_month: str | None = None,
        queried_at: datetime | None = None,
    ) -> ProviderHistorySymbol:
        """Insert or update a monthly quota row after a successful history request."""
        ym = year_month or utc_year_month()
        at = queried_at if queried_at is not None else datetime.now(UTC)
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)

        existing = self.get_by_key(
            provider=provider,
            provider_symbol=provider_symbol,
            year_month=ym,
        )
        if existing is not None:
            existing.last_queried_at = at
            existing.query_count = int(existing.query_count) + 1
            if instrument_id is not None:
                existing.instrument_id = instrument_id
            self._session.flush()
            return existing

        stmt = (
            insert(ProviderHistorySymbol)
            .values(
                provider=provider,
                provider_symbol=provider_symbol,
                year_month=ym,
                instrument_id=instrument_id,
                first_queried_at=at,
                last_queried_at=at,
                query_count=1,
            )
            .on_conflict_do_update(
                constraint="uq_provider_history_symbol_month",
                set_={
                    "last_queried_at": at,
                    "query_count": ProviderHistorySymbol.query_count + 1,
                    "updated_at": func.now(),
                },
            )
            .returning(ProviderHistorySymbol.id)
        )
        row_id = self._session.execute(stmt).scalar_one()
        self._session.expire_all()
        row = self.get_by_id(row_id)
        if row is None:  # pragma: no cover
            msg = f"record_query failed to load id={row_id}"
            raise RuntimeError(msg)
        if instrument_id is not None and row.instrument_id != instrument_id:
            row.instrument_id = instrument_id
            self._session.flush()
        return row

    def get_by_id(self, row_id: int) -> ProviderHistorySymbol | None:
        """Fetch by primary key."""
        return self._session.get(ProviderHistorySymbol, row_id)

    def get_by_key(
        self,
        *,
        provider: str,
        provider_symbol: str,
        year_month: str,
    ) -> ProviderHistorySymbol | None:
        """Fetch by unique business key."""
        stmt = select(ProviderHistorySymbol).where(
            ProviderHistorySymbol.provider == provider,
            ProviderHistorySymbol.provider_symbol == provider_symbol,
            ProviderHistorySymbol.year_month == year_month,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_by_month(
        self,
        *,
        provider: str,
        year_month: str,
    ) -> list[ProviderHistorySymbol]:
        """All symbols recorded for provider in ``year_month``, ordered by symbol."""
        stmt = (
            select(ProviderHistorySymbol)
            .where(
                ProviderHistorySymbol.provider == provider,
                ProviderHistorySymbol.year_month == year_month,
            )
            .order_by(ProviderHistorySymbol.provider_symbol)
        )
        return list(self._session.scalars(stmt).all())

    def count_by_month(self, *, provider: str, year_month: str) -> int:
        """Number of unique symbols recorded for the month."""
        stmt = (
            select(func.count())
            .select_from(ProviderHistorySymbol)
            .where(
                ProviderHistorySymbol.provider == provider,
                ProviderHistorySymbol.year_month == year_month,
            )
        )
        return int(self._session.execute(stmt).scalar_one())

    def has_query(
        self,
        *,
        provider: str,
        provider_symbol: str,
        year_month: str,
    ) -> bool:
        """True if this symbol was already recorded for the month."""
        return (
            self.get_by_key(
                provider=provider,
                provider_symbol=provider_symbol,
                year_month=year_month,
            )
            is not None
        )
