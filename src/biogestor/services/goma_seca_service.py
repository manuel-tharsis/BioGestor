from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.goma_seca_production import GomaSecaProduction
from biogestor.repositories.goma_seca_repository import GomaSecaRepository
from biogestor.services.audit_service import log_action


@dataclass(frozen=True)
class GomaSecaPayload:
    production_date: date
    lot_code: str
    finision_number: int
    kg_produced: float
    humidity_percent: float
    observations: str


class GomaSecaService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_production(
        self,
        *,
        payload: GomaSecaPayload,
        username: str,
    ) -> GomaSecaProduction:
        normalized_lot = payload.lot_code.strip().upper()
        if not normalized_lot:
            raise ValueError("El lote es obligatorio.")

        week_start = payload.production_date - timedelta(days=payload.production_date.weekday())

        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            existing = repository.get_by_lot_code(normalized_lot)
            before_data = self._serialize(existing) if existing is not None else None

            if existing is None:
                production = GomaSecaProduction(
                    production_date=payload.production_date,
                    week_start=week_start,
                    lot_code=normalized_lot,
                    finision_number=payload.finision_number,
                    kg_produced=payload.kg_produced,
                    humidity_percent=payload.humidity_percent,
                    observations=payload.observations.strip(),
                    created_by=username,
                )
                repository.save(production)
                action = "CREATE"
                description = f"Alta de produccion de goma seca para lote {normalized_lot}."
            else:
                existing.production_date = payload.production_date
                existing.week_start = week_start
                existing.finision_number = payload.finision_number
                existing.kg_produced = payload.kg_produced
                existing.humidity_percent = payload.humidity_percent
                existing.observations = payload.observations.strip()
                production = existing
                action = "UPDATE"
                description = f"Actualizacion de produccion de goma seca para lote {normalized_lot}."

            session.flush()
            after_data = self._serialize(production)
            screen = f"SEMANA_{payload.production_date.isocalendar().week}"
            log_action(
                session,
                username=username,
                module="PRODUCCIONES",
                section="GOMA_SECA",
                screen=screen,
                action=action,
                entity="GomaSecaProduction",
                entity_id=str(production.id),
                description=description,
                before_data=before_data,
                after_data=after_data,
            )
            session.commit()
            session.refresh(production)
            session.expunge(production)
            return production

    def list_by_week(self, week_start: date) -> list[GomaSecaProduction]:
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            items = list(repository.list_by_week(week_start))
            for item in items:
                session.expunge(item)
            return items

    def search(
        self,
        *,
        week_start: date | None = None,
        lot_contains: str | None = None,
    ) -> list[GomaSecaProduction]:
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            items = list(
                repository.search(
                    week_start=week_start,
                    lot_contains=lot_contains.strip().upper() if lot_contains else None,
                )
            )
            for item in items:
                session.expunge(item)
            return items

    @staticmethod
    def _serialize(production: GomaSecaProduction | None) -> dict[str, object] | None:
        if production is None:
            return None
        return {
            "production_date": production.production_date.isoformat(),
            "week_start": production.week_start.isoformat(),
            "lot_code": production.lot_code,
            "finision_number": production.finision_number,
            "kg_produced": production.kg_produced,
            "humidity_percent": production.humidity_percent,
            "observations": production.observations,
            "created_by": production.created_by,
        }
