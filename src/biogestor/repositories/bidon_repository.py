from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from biogestor.db.models.bidon import Bidon


class BidonRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_identification(self, identification: str) -> Bidon | None:
        stmt = select(Bidon).where(Bidon.identification == identification)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[Bidon]:
        stmt = select(Bidon).order_by(Bidon.identification.asc())
        return self.session.execute(stmt).scalars().all()

    def search(
        self,
        *,
        identification_contains: str | None = None,
        status: str | None = None,
    ) -> Sequence[Bidon]:
        stmt = select(Bidon)
        if identification_contains:
            stmt = stmt.where(Bidon.identification.ilike(f"%{identification_contains}%"))
        if status and status != "todos":
            stmt = stmt.where(Bidon.status == status)
        stmt = stmt.order_by(Bidon.identification.asc())
        return self.session.execute(stmt).scalars().all()

    def save(self, bidon: Bidon) -> Bidon:
        self.session.add(bidon)
        return bidon

    def list_identifications(
        self,
        *,
        contains: str | None = None,
        status: str | None = None,
    ) -> list[str]:
        stmt = select(Bidon.identification)
        if contains:
            stmt = stmt.where(Bidon.identification.ilike(f"%{contains}%"))
        if status and status != "todos":
            stmt = stmt.where(Bidon.status == status)
        stmt = stmt.order_by(Bidon.identification.asc())
        return list(self.session.execute(stmt).scalars().all())
