from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.solvent_week_metric import SolventWeekMetric
from biogestor.repositories.solvent_week_metric_repository import (
    SolventWeekMetricRepository,
)


@dataclass(frozen=True)
class SolventWeekSnapshot:
    solvent_name: str
    week_start: date
    purchases_liters: float
    stock_liters: float
    consumed_liters: float
    has_data: bool


class SolventWeekMetricService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_snapshot(self, *, solvent_name: str, week_start: date) -> SolventWeekSnapshot:
        normalized = solvent_name.strip().lower()
        with self._session_factory() as session:
            repository = SolventWeekMetricRepository(session)
            metric = repository.get_by_solvent_and_week(
                solvent_name=normalized,
                week_start=week_start,
            )
            if metric is None:
                return SolventWeekSnapshot(
                    solvent_name=normalized,
                    week_start=week_start,
                    purchases_liters=0.0,
                    stock_liters=0.0,
                    consumed_liters=0.0,
                    has_data=False,
                )

            session.expunge(metric)
            return self._to_snapshot(metric)

    def save_snapshot(
        self,
        *,
        solvent_name: str,
        week_start: date,
        purchases_liters: float,
        stock_liters: float,
        consumed_liters: float,
    ) -> SolventWeekSnapshot:
        normalized = solvent_name.strip().lower()
        with self._session_factory() as session:
            repository = SolventWeekMetricRepository(session)
            metric = repository.get_by_solvent_and_week(
                solvent_name=normalized,
                week_start=week_start,
            )
            if metric is None:
                metric = SolventWeekMetric(
                    solvent_name=normalized,
                    week_start=week_start,
                    purchases_liters=purchases_liters,
                    stock_liters=stock_liters,
                    consumed_liters=consumed_liters,
                )
                repository.save(metric)
            else:
                metric.purchases_liters = purchases_liters
                metric.stock_liters = stock_liters
                metric.consumed_liters = consumed_liters
            session.commit()
            session.refresh(metric)
            session.expunge(metric)
            return self._to_snapshot(metric)

    @staticmethod
    def _to_snapshot(metric: SolventWeekMetric) -> SolventWeekSnapshot:
        return SolventWeekSnapshot(
            solvent_name=metric.solvent_name,
            week_start=metric.week_start,
            purchases_liters=metric.purchases_liters,
            stock_liters=metric.stock_liters,
            consumed_liters=metric.consumed_liters,
            has_data=True,
        )
