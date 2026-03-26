from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.services.bidon_service import BidonPayload, BidonService
from biogestor.services.goma_seca_service import GomaSecaPayload, GomaSecaService
from biogestor.services.solvent_week_metric_service import SolventWeekMetricService


def _session_factory() -> sessionmaker:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_goma_seca_service_saves_and_queries_week_records() -> None:
    service = GomaSecaService(_session_factory())

    saved = service.save_production(
        payload=GomaSecaPayload(
            production_date=date(2026, 3, 24),
            lot_code="eg26-083-1",
            finision_number=1,
            kg_produced=1200.5,
            humidity_percent=8.2,
            observations="turno de manana",
        ),
        username="juana",
    )

    assert saved.lot_code == "EG26-083-1"

    week_items = service.list_by_week(date(2026, 3, 23))

    assert len(week_items) == 1
    assert week_items[0].kg_produced == 1200.5

    search_items = service.search(lot_contains="083")

    assert len(search_items) == 1
    assert search_items[0].observations == "turno de manana"


def test_bidon_service_saves_and_filters_bidones() -> None:
    service = BidonService(_session_factory())

    service.save_bidon(
        payload=BidonPayload(
            identification="b-1001",
            status="stock",
            consumed_in=None,
            notes="disponible",
        ),
        username="juana",
    )
    service.save_bidon(
        payload=BidonPayload(
            identification="b-1002",
            status="consumido",
            consumed_in="f0975",
            notes="consumido en formula",
        ),
        username="juana",
    )

    stock_items = service.search(status="stock")
    consumed_items = service.search(status="consumido")

    assert len(stock_items) == 1
    assert stock_items[0].identification == "B-1001"
    assert len(consumed_items) == 1
    assert consumed_items[0].consumed_in == "f0975"
    assert service.list_identifications("100") == ["B-1001", "B-1002"]


def test_solvent_week_metric_service_returns_empty_and_saved_snapshots() -> None:
    service = SolventWeekMetricService(_session_factory())
    week = date(2026, 3, 23)

    empty = service.get_snapshot(solvent_name="hexano", week_start=week)

    assert not empty.has_data
    assert empty.stock_liters == 0.0

    saved = service.save_snapshot(
        solvent_name="hexano",
        week_start=week,
        purchases_liters=12000,
        stock_liters=9000,
        consumed_liters=2200,
    )

    assert saved.has_data
    assert saved.purchases_liters == 12000

    loaded = service.get_snapshot(solvent_name="hexano", week_start=week)

    assert loaded.has_data
    assert loaded.consumed_liters == 2200
