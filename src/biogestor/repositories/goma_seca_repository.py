from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from biogestor.db.models.goma_seca_production import GomaSecaProduction


class GomaSecaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, record_id: int) -> GomaSecaProduction | None:
        stmt = select(GomaSecaProduction).where(GomaSecaProduction.id == record_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_lot_code(self, lot_code: str) -> GomaSecaProduction | None:
        stmt = select(GomaSecaProduction).where(GomaSecaProduction.lot_code == lot_code)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_day_and_finision(
        self,
        production_date: date,
        finision_number: int,
    ) -> GomaSecaProduction | None:
        stmt = select(GomaSecaProduction).where(
            GomaSecaProduction.production_date == production_date,
            GomaSecaProduction.finision_number == finision_number,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_by_day(self, production_date: date) -> Sequence[GomaSecaProduction]:
        stmt = (
            select(GomaSecaProduction)
            .where(GomaSecaProduction.production_date == production_date)
            .order_by(GomaSecaProduction.finision_number.asc())
        )
        return self.session.execute(stmt).scalars().all()

    def list_by_week(self, week_start: date) -> Sequence[GomaSecaProduction]:
        stmt = (
            select(GomaSecaProduction)
            .where(GomaSecaProduction.week_start == week_start)
            .order_by(
                GomaSecaProduction.production_date.asc(),
                GomaSecaProduction.finision_number.asc(),
                GomaSecaProduction.id.asc(),
            )
        )
        return self.session.execute(stmt).scalars().all()

    def search(
        self,
        *,
        week_start: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        lot_contains: str | None = None,
    ) -> Sequence[GomaSecaProduction]:
        stmt = select(GomaSecaProduction)
        if week_start is not None:
            stmt = stmt.where(GomaSecaProduction.week_start == week_start)
        if date_from is not None:
            stmt = stmt.where(GomaSecaProduction.production_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(GomaSecaProduction.production_date <= date_to)
        if lot_contains:
            stmt = stmt.where(GomaSecaProduction.lot_code.ilike(f"%{lot_contains}%"))
        stmt = stmt.order_by(
            GomaSecaProduction.production_date.desc(),
            GomaSecaProduction.id.desc(),
        )
        return self.session.execute(stmt).scalars().all()

    def get_by_raw_drum_identification(self, identification: str) -> GomaSecaProduction | None:
        stmt = (
            select(GomaSecaProduction)
            .where(GomaSecaProduction.raw_drum_identification == identification)
            .order_by(GomaSecaProduction.production_date.desc(), GomaSecaProduction.id.desc())
        )
        return self.session.execute(stmt).scalars().first()

    def save(self, production: GomaSecaProduction) -> GomaSecaProduction:
        self.session.add(production)
        return production
