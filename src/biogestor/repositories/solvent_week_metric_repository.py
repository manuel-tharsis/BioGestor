from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from biogestor.db.models.solvent_week_metric import SolventWeekMetric


class SolventWeekMetricRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_solvent_and_week(
        self,
        *,
        solvent_name: str,
        week_start: date,
    ) -> SolventWeekMetric | None:
        stmt = select(SolventWeekMetric).where(
            SolventWeekMetric.solvent_name == solvent_name,
            SolventWeekMetric.week_start == week_start,
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def save(self, metric: SolventWeekMetric) -> SolventWeekMetric:
        self.session.add(metric)
        return metric
