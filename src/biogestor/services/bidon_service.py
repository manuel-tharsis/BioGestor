from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.bidon import Bidon
from biogestor.repositories.bidon_repository import BidonRepository
from biogestor.services.audit_service import log_action


@dataclass(frozen=True)
class BidonPayload:
    identification: str
    status: str
    consumed_in: str | None
    notes: str


class BidonService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_bidon(self, *, payload: BidonPayload, username: str) -> Bidon:
        identification = payload.identification.strip().upper()
        if not identification:
            raise ValueError("La identificacion es obligatoria.")

        normalized_status = payload.status.strip().lower()
        normalized_consumption = (payload.consumed_in or "").strip().lower() or None
        if normalized_status == "stock":
            normalized_consumption = None

        with self._session_factory() as session:
            repository = BidonRepository(session)
            existing = repository.get_by_identification(identification)
            before_data = self._serialize(existing) if existing is not None else None

            if existing is None:
                bidon = Bidon(
                    identification=identification,
                    status=normalized_status,
                    consumed_in=normalized_consumption,
                    notes=payload.notes.strip(),
                    created_by=username,
                )
                repository.save(bidon)
                action = "CREATE"
                description = f"Alta de bidon {identification}."
            else:
                existing.status = normalized_status
                existing.consumed_in = normalized_consumption
                existing.notes = payload.notes.strip()
                bidon = existing
                action = "UPDATE"
                description = f"Actualizacion de bidon {identification}."

            session.flush()
            log_action(
                session,
                username=username,
                module="STOCK",
                section="BIDONES",
                screen="LISTADO_BIDONES",
                action=action,
                entity="Bidon",
                entity_id=str(bidon.id),
                description=description,
                before_data=before_data,
                after_data=self._serialize(bidon),
            )
            session.commit()
            session.refresh(bidon)
            session.expunge(bidon)
            return bidon

    def list_bidones(self) -> list[Bidon]:
        with self._session_factory() as session:
            repository = BidonRepository(session)
            items = list(repository.list_all())
            for item in items:
                session.expunge(item)
            return items

    def search(self, *, identification_contains: str | None = None, status: str | None = None) -> list[Bidon]:
        with self._session_factory() as session:
            repository = BidonRepository(session)
            items = list(
                repository.search(
                    identification_contains=(
                        identification_contains.strip().upper() if identification_contains else None
                    ),
                    status=status,
                )
            )
            for item in items:
                session.expunge(item)
            return items

    def list_identifications(self, contains: str | None = None) -> list[str]:
        normalized = contains.strip().upper() if contains else None
        with self._session_factory() as session:
            repository = BidonRepository(session)
            return repository.list_identifications(contains=normalized)

    @staticmethod
    def _serialize(bidon: Bidon | None) -> dict[str, object] | None:
        if bidon is None:
            return None
        return {
            "identification": bidon.identification,
            "status": bidon.status,
            "consumed_in": bidon.consumed_in,
            "notes": bidon.notes,
            "created_by": bidon.created_by,
        }
