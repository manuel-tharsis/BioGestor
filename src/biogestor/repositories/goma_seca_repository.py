from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from biogestor.db.models.goma_seca_production import GomaSecaProduction


class GomaSecaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_lot_code(self, lot_code: str) -> GomaSecaProduction | None:
        stmt = select(GomaSecaProduction).where(GomaSecaProduction.lot_code == lot_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_week(self, week_start: date) -> Sequence[GomaSecaProduction]:
        stmt = (
            select(GomaSecaProduction)
            .where(GomaSecaProduction.week_start == week_start)
            .order_by(GomaSecaProduction.production_date.asc(), GomaSecaProduction.id.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def search(
        self,
        *,
        week_start: date | None = None,
        lot_contains: str | None = None,
    ) -> Sequence[GomaSecaProduction]:
        stmt = select(GomaSecaProduction)
        if week_start is not None:
            stmt = stmt.where(GomaSecaProduction.week_start == week_start)
        if lot_contains:
            stmt = stmt.where(GomaSecaProduction.lot_code.ilike(f"%{lot_contains}%"))
        stmt = stmt.order_by(
            GomaSecaProduction.production_date.desc(),
            GomaSecaProduction.id.desc(),
        )
        return self.session.execute(stmt).scalars().all()

    def save(self, production: GomaSecaProduction) -> GomaSecaProduction:
        self.session.add(production)
        return production
