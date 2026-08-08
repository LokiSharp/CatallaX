"""CRUD / upsert for instrument_symbol_map."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from catallax.db.models.instrument import InstrumentSymbolMap

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class InstrumentSymbolMapRepository:
    """Provider symbol mapping persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        instrument_id: int,
        provider: str,
        provider_symbol: str,
        provider_exchange: str = "",
        is_active: bool = True,
    ) -> InstrumentSymbolMap:
        """Insert a new mapping row."""
        row = InstrumentSymbolMap(
            instrument_id=instrument_id,
            provider=provider,
            provider_symbol=provider_symbol,
            provider_exchange=provider_exchange,
            is_active=is_active,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_id(self, map_id: int) -> InstrumentSymbolMap | None:
        """Fetch by primary key."""
        return self._session.get(InstrumentSymbolMap, map_id)

    def get_by_provider_key(
        self,
        *,
        provider: str,
        provider_symbol: str,
        provider_exchange: str = "",
    ) -> InstrumentSymbolMap | None:
        """Fetch by unique provider key."""
        stmt = select(InstrumentSymbolMap).where(
            InstrumentSymbolMap.provider == provider,
            InstrumentSymbolMap.provider_symbol == provider_symbol,
            InstrumentSymbolMap.provider_exchange == provider_exchange,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_by_instrument(self, instrument_id: int) -> list[InstrumentSymbolMap]:
        """All mappings for one instrument."""
        stmt = (
            select(InstrumentSymbolMap)
            .where(InstrumentSymbolMap.instrument_id == instrument_id)
            .order_by(InstrumentSymbolMap.provider, InstrumentSymbolMap.provider_symbol)
        )
        return list(self._session.scalars(stmt).all())

    def upsert(
        self,
        *,
        instrument_id: int,
        provider: str,
        provider_symbol: str,
        provider_exchange: str = "",
        is_active: bool = True,
    ) -> InstrumentSymbolMap:
        """Insert or update by (provider, provider_symbol, provider_exchange)."""
        stmt = (
            insert(InstrumentSymbolMap)
            .values(
                instrument_id=instrument_id,
                provider=provider,
                provider_symbol=provider_symbol,
                provider_exchange=provider_exchange,
                is_active=is_active,
            )
            .on_conflict_do_update(
                constraint="uq_symbol_map_provider_symbol_exchange",
                set_={
                    "instrument_id": instrument_id,
                    "is_active": is_active,
                    "updated_at": func.now(),
                },
            )
            .returning(InstrumentSymbolMap.id)
        )
        map_id = self._session.execute(stmt).scalar_one()
        self._session.expire_all()
        row = self.get_by_id(map_id)
        if row is None:  # pragma: no cover - defensive
            msg = f"upsert failed to load symbol map id={map_id}"
            raise RuntimeError(msg)
        return row
