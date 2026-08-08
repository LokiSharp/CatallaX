"""CRUD / upsert for the instrument table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from catallax.db.models.instrument import Instrument

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class InstrumentRepository:
    """Instrument persistence. Callers own the Session transaction boundary."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        symbol: str,
        market: str,
        exchange: str,
        name_cn: str,
        currency: str,
        name_en: str = "",
        name_hk: str = "",
        status: str = "active",
    ) -> Instrument:
        """Insert a new instrument row and flush to obtain its id."""
        row = Instrument(
            symbol=symbol,
            market=market,
            exchange=exchange,
            name_cn=name_cn,
            name_en=name_en,
            name_hk=name_hk,
            currency=currency,
            status=status,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, instrument_id: int) -> Instrument | None:
        """Fetch by primary key."""
        return self._session.get(Instrument, instrument_id)

    def get_by_business_key(
        self,
        *,
        market: str,
        symbol: str,
        exchange: str | None = None,
    ) -> Instrument | None:
        """Fetch by (market, symbol). ``exchange`` is ignored (legacy callers)."""
        _ = exchange
        stmt = select(Instrument).where(
            Instrument.market == market,
            Instrument.symbol == symbol,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_by_market(self, market: str) -> list[Instrument]:
        """Return all instruments for a market, ordered by symbol."""
        stmt = (
            select(Instrument)
            .where(Instrument.market == market)
            .order_by(Instrument.symbol)
        )
        return list(self._session.scalars(stmt).all())

    def update(
        self,
        instrument: Instrument,
        *,
        name_cn: str | None = None,
        name_en: str | None = None,
        name_hk: str | None = None,
        exchange: str | None = None,
        currency: str | None = None,
        status: str | None = None,
    ) -> Instrument:
        """Mutate mutable fields on an already-attached instrument."""
        fields: dict[str, object] = {
            "name_cn": name_cn,
            "name_en": name_en,
            "name_hk": name_hk,
            "exchange": exchange,
            "currency": currency,
            "status": status,
        }
        for attr, value in fields.items():
            if value is not None:
                setattr(instrument, attr, value)
        self._session.flush()
        return instrument

    def upsert_by_business_key(
        self,
        *,
        symbol: str,
        market: str,
        exchange: str,
        name_cn: str,
        currency: str,
        name_en: str = "",
        name_hk: str = "",
        status: str = "active",
    ) -> Instrument:
        """Insert or update by (market, symbol). Idempotent; exchange is updated."""
        stmt = (
            insert(Instrument)
            .values(
                symbol=symbol,
                market=market,
                exchange=exchange,
                name_cn=name_cn,
                name_en=name_en,
                name_hk=name_hk,
                currency=currency,
                status=status,
            )
            .on_conflict_do_update(
                constraint="uq_instrument_market_symbol",
                set_={
                    "name_cn": name_cn,
                    "name_en": name_en,
                    "name_hk": name_hk,
                    "exchange": exchange,
                    "currency": currency,
                    "status": status,
                    "updated_at": func.now(),
                },
            )
            .returning(Instrument.id)
        )
        instrument_id = self._session.execute(stmt).scalar_one()
        self._session.expire_all()
        row = self.get_by_id(instrument_id)
        if row is None:  # pragma: no cover - defensive
            msg = f"upsert failed to load instrument id={instrument_id}"
            raise RuntimeError(msg)
        return row
