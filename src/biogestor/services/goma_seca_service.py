from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.audit_log import AuditLog
from biogestor.db.models.goma_seca_production import GomaSecaProduction
from biogestor.repositories.bidon_repository import BidonRepository
from biogestor.repositories.goma_seca_repository import GomaSecaRepository
from biogestor.services.audit_service import log_action


@dataclass(frozen=True)
class GomaSecaPayload:
    production_date: date
    lot_code: str
    finision_number: int
    kg_produced: float
    raw_drum_identification: str
    raw_kg_used: float
    filter_cleanings: int
    humidity_percent: float
    day_start_time: str
    top_temperature: float
    gum_temperature: float
    vacuum: float
    distillation_minutes: int
    observations: str


class GomaSecaService:
    MAX_FINISION = 4
    MAX_RAW_BIDON_KG = 250.0
    STANDARD_RAW_BIDON_KG = 200.0
    PRODUCED_KG_STEP = 25.0

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_production(
        self,
        *,
        payload: GomaSecaPayload,
        username: str,
        record_id: int | None = None,
    ) -> GomaSecaProduction:
        normalized_lot = payload.lot_code.strip().upper()
        normalized_bidon = payload.raw_drum_identification.strip().upper()
        normalized_time = payload.day_start_time.strip()
        if not normalized_lot:
            raise ValueError("El lote es obligatorio.")
        if not normalized_bidon:
            raise ValueError("El número de bidón de goma bruta es obligatorio.")
        if not normalized_time:
            raise ValueError("La hora de inicio del día es obligatoria.")
        if payload.finision_number < 1 or payload.finision_number > self.MAX_FINISION:
            raise ValueError("La finisión debe estar entre 1 y 4.")
        if payload.kg_produced <= 0:
            raise ValueError("Los kg producidos deben ser mayores que cero.")
        if payload.raw_kg_used <= 0:
            raise ValueError("Los kg de goma bruta deben ser mayores que cero.")
        if payload.raw_kg_used > self.MAX_RAW_BIDON_KG:
            raise ValueError("Los kg de goma bruta no pueden superar los 250 kg.")
        if payload.kg_produced > payload.raw_kg_used:
            raise ValueError("Los kg producidos no pueden superar los kg consumidos de goma bruta.")
        if not self._is_multiple_of_step(payload.kg_produced, self.PRODUCED_KG_STEP):
            raise ValueError("Los kg producidos deben ser múltiplos de 25 kg.")
        if payload.filter_cleanings < 0:
            raise ValueError("El número de limpiezas no puede ser negativo.")
        if payload.distillation_minutes < 0:
            raise ValueError("El tiempo de destilación no puede ser negativo.")

        week_start = payload.production_date - timedelta(days=payload.production_date.weekday())

        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            bidon_repository = BidonRepository(session)
            self._validate_finision_sequence(
                repository,
                payload.production_date,
                payload.finision_number,
            )

            duplicated_lot = repository.get_by_lot_code(normalized_lot)
            if duplicated_lot is not None and duplicated_lot.id != record_id:
                raise ValueError("El número de lote no se puede repetir.")

            existing_in_slot = repository.get_by_day_and_finision(
                payload.production_date,
                payload.finision_number,
            )
            if record_id is None and existing_in_slot is not None:
                raise ValueError("Ya hay datos guardados para ese día y finisión.")

            if record_id is not None:
                production = repository.get_by_id(record_id)
                if production is None:
                    raise ValueError("No se ha encontrado el registro a editar.")
                if (
                    production.production_date != payload.production_date
                    or production.finision_number != payload.finision_number
                ):
                    raise ValueError("La edición debe mantenerse en el mismo día y finisión.")
                before_data = self._serialize(production)
                action = "UPDATE"
                description = f"Actualización de producción de goma seca para lote {normalized_lot}."
                previous_bidon_identification = production.raw_drum_identification
            else:
                production = GomaSecaProduction(
                    production_date=payload.production_date,
                    week_start=week_start,
                    lot_code=normalized_lot,
                    finision_number=payload.finision_number,
                    kg_produced=payload.kg_produced,
                    raw_drum_identification=normalized_bidon,
                    raw_kg_used=payload.raw_kg_used,
                    filter_cleanings=payload.filter_cleanings,
                    humidity_percent=payload.humidity_percent,
                    day_start_time=normalized_time,
                    top_temperature=payload.top_temperature,
                    gum_temperature=payload.gum_temperature,
                    vacuum=payload.vacuum,
                    distillation_minutes=payload.distillation_minutes,
                    observations=payload.observations.strip(),
                    created_by=username,
                )
                repository.save(production)
                before_data = None
                action = "CREATE"
                description = f"Alta de producción de goma seca para lote {normalized_lot}."
                previous_bidon_identification = None

            self._ensure_bidon_available(
                bidon_repository,
                normalized_bidon,
                current_bidon_identification=previous_bidon_identification,
            )

            production.production_date = payload.production_date
            production.week_start = week_start
            production.lot_code = normalized_lot
            production.finision_number = payload.finision_number
            production.kg_produced = payload.kg_produced
            production.raw_drum_identification = normalized_bidon
            production.raw_kg_used = payload.raw_kg_used
            production.filter_cleanings = payload.filter_cleanings
            production.humidity_percent = payload.humidity_percent
            production.day_start_time = normalized_time
            production.top_temperature = payload.top_temperature
            production.gum_temperature = payload.gum_temperature
            production.vacuum = payload.vacuum
            production.distillation_minutes = payload.distillation_minutes
            production.observations = payload.observations.strip()

            if previous_bidon_identification and previous_bidon_identification != normalized_bidon:
                self._release_bidon_if_needed(bidon_repository, previous_bidon_identification)
            self._consume_bidon(bidon_repository, normalized_bidon)

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

    def clear_all_data(self, *, username: str = "system") -> int:
        with self._session_factory() as session:
            productions = session.execute(select(GomaSecaProduction)).scalars().all()
            deleted_count = len(productions)
            bidon_repository = BidonRepository(session)

            for production in productions:
                self._release_bidon_if_needed(bidon_repository, production.raw_drum_identification)

            if deleted_count:
                log_action(
                    session,
                    username=username,
                    module="PRODUCCIONES",
                    section="GOMA_SECA",
                    screen="ADMIN",
                    action="DELETE_ALL",
                    entity="GomaSecaProduction",
                    entity_id="all",
                    description="Eliminación completa de datos de producción de goma seca.",
                    before_data={"count": deleted_count},
                    after_data={"count": 0},
                )

            session.execute(delete(GomaSecaProduction))
            session.execute(delete(AuditLog).where(AuditLog.section == "GOMA_SECA"))
            session.commit()
            return deleted_count

    def get_slot(self, production_date: date, finision_number: int) -> GomaSecaProduction | None:
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            item = repository.get_by_day_and_finision(production_date, finision_number)
            if item is not None:
                session.expunge(item)
            return item

    def list_by_day(self, production_date: date) -> list[GomaSecaProduction]:
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            items = list(repository.list_by_day(production_date))
            for item in items:
                session.expunge(item)
            return items

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
        date_from: date | None = None,
        date_to: date | None = None,
        lot_contains: str | None = None,
    ) -> list[GomaSecaProduction]:
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            items = list(
                repository.search(
                    week_start=week_start,
                    date_from=date_from,
                    date_to=date_to,
                    lot_contains=lot_contains.strip().upper() if lot_contains else None,
                )
            )
            for item in items:
                session.expunge(item)
            return items

    def list_lots(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[str]:
        items = self.search(date_from=date_from, date_to=date_to)
        return sorted({item.lot_code for item in items})

    def get_by_raw_drum_identification(self, identification: str) -> GomaSecaProduction | None:
        normalized = identification.strip().upper()
        if not normalized:
            return None
        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            item = repository.get_by_raw_drum_identification(normalized)
            if item is not None:
                session.expunge(item)
            return item

    def validate_lot(
        self,
        *,
        lot_code: str,
        production_date: date,
        finision_number: int,
        record_id: int | None = None,
    ) -> tuple[bool, str]:
        normalized_lot = lot_code.strip().upper()
        if not normalized_lot:
            return False, "Introduce un lote para poder guardar."
        if payload_finision_invalid(finision_number, self.MAX_FINISION):
            return False, "La finisión debe estar entre 1 y 4."

        with self._session_factory() as session:
            repository = GomaSecaRepository(session)
            if repository.get_by_lot_code(normalized_lot) is not None:
                duplicated = repository.get_by_lot_code(normalized_lot)
                if duplicated is not None and duplicated.id != record_id:
                    return False, "El número de lote no se puede repetir."

            for previous_finision in range(1, finision_number):
                previous = repository.get_by_day_and_finision(production_date, previous_finision)
                if previous is None:
                    return (
                        False,
                        f"No puede haber una finisión {finision_number} sin la {previous_finision}.",
                    )

        return True, "Lote válido. Puedes guardar la producción."

    def _validate_finision_sequence(
        self,
        repository: GomaSecaRepository,
        production_date: date,
        finision_number: int,
    ) -> None:
        for previous_finision in range(1, finision_number):
            previous = repository.get_by_day_and_finision(production_date, previous_finision)
            if previous is None:
                raise ValueError(
                    f"No puede haber una finisión {finision_number} sin la {previous_finision}."
                )

    @staticmethod
    def _ensure_bidon_available(
        repository: BidonRepository,
        bidon_identification: str,
        *,
        current_bidon_identification: str | None,
    ) -> None:
        bidon = repository.get_by_identification(bidon_identification)
        if bidon is None:
            raise ValueError("El bidón indicado no existe.")
        if bidon.status == "stock":
            return
        if current_bidon_identification and bidon.identification == current_bidon_identification:
            return
        raise ValueError("El bidón seleccionado ya ha sido consumido y no puede reutilizarse.")

    @staticmethod
    def _consume_bidon(repository: BidonRepository, bidon_identification: str) -> None:
        bidon = repository.get_by_identification(bidon_identification)
        if bidon is None:
            return
        bidon.status = "consumido"
        bidon.consumed_in = "f1620"

    @staticmethod
    def _release_bidon_if_needed(repository: BidonRepository, bidon_identification: str) -> None:
        bidon = repository.get_by_identification(bidon_identification)
        if bidon is None:
            return
        if bidon.consumed_in != "f1620":
            return
        bidon.status = "stock"
        bidon.consumed_in = None

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
            "raw_drum_identification": production.raw_drum_identification,
            "raw_kg_used": production.raw_kg_used,
            "filter_cleanings": production.filter_cleanings,
            "humidity_percent": production.humidity_percent,
            "day_start_time": production.day_start_time,
            "top_temperature": production.top_temperature,
            "gum_temperature": production.gum_temperature,
            "vacuum": production.vacuum,
            "distillation_minutes": production.distillation_minutes,
            "observations": production.observations,
            "created_by": production.created_by,
        }

    @staticmethod
    def _is_multiple_of_step(value: float, step: float) -> bool:
        remainder = value % step
        return remainder < 1e-6 or abs(remainder - step) < 1e-6


def payload_finision_invalid(finision_number: int, max_finision: int) -> bool:
    return finision_number < 1 or finision_number > max_finision
