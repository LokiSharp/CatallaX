"""CRUD / upsert for fundamental_period."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from catallax.db.models.fundamental import FundamentalPeriod

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal

    from sqlalchemy.orm import Session


class FundamentalPeriodRepository:
    """Fiscal-period fundamentals persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(
        self,
        *,
        instrument_id: int,
        period_end: date,
        source: str,
    ) -> FundamentalPeriod | None:
        """Fetch by primary key."""
        return self._session.get(
            FundamentalPeriod,
            {
                "instrument_id": instrument_id,
                "period_end": period_end,
                "source": source,
            },
        )

    def list_by_instrument(
        self,
        instrument_id: int,
        *,
        source: str | None = None,
    ) -> list[FundamentalPeriod]:
        """All periods for an instrument, ascending by period_end."""
        stmt = select(FundamentalPeriod).where(
            FundamentalPeriod.instrument_id == instrument_id,
        )
        if source is not None:
            stmt = stmt.where(FundamentalPeriod.source == source)
        stmt = stmt.order_by(FundamentalPeriod.period_end.asc())
        return list(self._session.scalars(stmt).all())

    def latest_as_of(
        self,
        *,
        instrument_id: int,
        as_of_date: date,
        source: str | None = None,
        require_available_date: bool = True,
    ) -> FundamentalPeriod | None:
        """Latest period usable at ``as_of_date`` under PIT rules.

        When ``require_available_date`` is True (default), only rows with
        non-null ``available_date <= as_of_date`` are considered. Rows without
        ``available_date`` are excluded so PE/PB cannot look ahead by accident.
        """
        stmt = select(FundamentalPeriod).where(
            FundamentalPeriod.instrument_id == instrument_id,
        )
        if source is not None:
            stmt = stmt.where(FundamentalPeriod.source == source)
        if require_available_date:
            stmt = stmt.where(
                FundamentalPeriod.available_date.is_not(None),
                FundamentalPeriod.available_date <= as_of_date,
            )
        else:
            # Unsafe fallback: period_end only (not for production PE/PB).
            stmt = stmt.where(FundamentalPeriod.period_end <= as_of_date)
        stmt = stmt.order_by(
            FundamentalPeriod.period_end.desc(),
            FundamentalPeriod.available_date.desc().nulls_last(),
        ).limit(1)
        return self._session.scalars(stmt).first()

    def upsert(
        self,
        *,
        instrument_id: int,
        period_end: date,
        period_label: str,
        source: str,
        currency: str,
        eps: Decimal | None = None,
        bps: Decimal | None = None,
        fiscal_year: int | None = None,
        announcement_date: date | None = None,
        available_date: date | None = None,
    ) -> FundamentalPeriod:
        """Insert or update by (instrument_id, period_end, source)."""
        stmt = (
            insert(FundamentalPeriod)
            .values(
                instrument_id=instrument_id,
                period_end=period_end,
                period_label=period_label,
                fiscal_year=fiscal_year,
                eps=eps,
                bps=bps,
                currency=currency,
                announcement_date=announcement_date,
                available_date=available_date,
                source=source,
            )
            .on_conflict_do_update(
                constraint="pk_fundamental_period",
                set_={
                    "period_label": period_label,
                    "fiscal_year": fiscal_year,
                    "eps": eps,
                    "bps": bps,
                    "currency": currency,
                    "announcement_date": announcement_date,
                    "available_date": available_date,
                    "updated_at": func.now(),
                },
            )
            .returning(
                FundamentalPeriod.instrument_id,
                FundamentalPeriod.period_end,
                FundamentalPeriod.source,
            )
        )
        row = self._session.execute(stmt).one()
        self._session.expire_all()
        loaded = self.get(
            instrument_id=row.instrument_id,
            period_end=row.period_end,
            source=row.source,
        )
        if loaded is None:  # pragma: no cover
            msg = "upsert failed to reload fundamental_period"
            raise RuntimeError(msg)
        return loaded
