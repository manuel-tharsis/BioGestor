from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.db.init_db import ensure_default_bidones
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
    session_factory = _session_factory()
    service = GomaSecaService(session_factory)
    bidon_service = BidonService(session_factory)
    bidon_service.save_bidon(
        payload=BidonPayload("p001", "stock", None, ""),
        username="juana",
    )

    saved = service.save_production(
        payload=GomaSecaPayload(
            production_date=date(2026, 3, 24),
            lot_code="eg26-083-1",
            finision_number=1,
            kg_produced=1200.5,
            raw_drum_identification="p001",
            raw_kg_used=1420.0,
            filter_cleanings=2,
            humidity_percent=8.2,
            day_start_time="07:15",
            top_temperature=82.5,
            gum_temperature=76.1,
            vacuum=-0.85,
            distillation_minutes=95,
            observations="turno de manana",
        ),
        username="juana",
    )

    assert saved.lot_code == "EG26-083-1"
    assert saved.raw_drum_identification == "P001"

    week_items = service.list_by_week(date(2026, 3, 23))

    assert len(week_items) == 1
    assert week_items[0].kg_produced == 1200.5
    assert week_items[0].raw_kg_used == 1420.0

    search_items = service.search(lot_contains="083")

    assert len(search_items) == 1
    assert search_items[0].observations == "turno de manana"
    assert service.get_slot(date(2026, 3, 24), 1) is not None

    updated_bidon = bidon_service.search(identification_contains="P001", status="consumido")
    assert len(updated_bidon) == 1
    assert updated_bidon[0].consumed_in == "f1620"


def test_goma_seca_service_requires_previous_finision() -> None:
    session_factory = _session_factory()
    service = GomaSecaService(session_factory)
    bidon_service = BidonService(session_factory)
    bidon_service.save_bidon(
        payload=BidonPayload("P002", "stock", None, ""),
        username="juana",
    )

    try:
        service.save_production(
            payload=GomaSecaPayload(
                production_date=date(2026, 3, 24),
                lot_code="EG26-084-2",
                finision_number=2,
                kg_produced=900,
                raw_drum_identification="P002",
                raw_kg_used=1000,
                filter_cleanings=1,
                humidity_percent=7.9,
                day_start_time="08:00",
                top_temperature=80,
                gum_temperature=74,
                vacuum=-0.80,
                distillation_minutes=90,
                observations="",
            ),
            username="juana",
        )
    except ValueError as exc:
        assert "sin la 1" in str(exc)
    else:
        raise AssertionError("Se esperaba un error por finision no consecutiva.")


def test_goma_seca_service_clears_all_data_and_releases_bidones() -> None:
    session_factory = _session_factory()
    service = GomaSecaService(session_factory)
    bidon_service = BidonService(session_factory)
    bidon_service.save_bidon(
        payload=BidonPayload("P003", "stock", None, ""),
        username="juana",
    )

    service.save_production(
        payload=GomaSecaPayload(
            production_date=date(2026, 3, 24),
            lot_code="EG26-083-1",
            finision_number=1,
            kg_produced=1200.5,
            raw_drum_identification="P003",
            raw_kg_used=1420.0,
            filter_cleanings=2,
            humidity_percent=8.2,
            day_start_time="07:15",
            top_temperature=82.5,
            gum_temperature=76.1,
            vacuum=-0.85,
            distillation_minutes=95,
            observations="turno de manana",
        ),
        username="juana",
    )

    deleted = service.clear_all_data(username="juana")
    released = bidon_service.search(identification_contains="P003", status="stock")

    assert deleted == 1
    assert service.list_by_week(date(2026, 3, 23)) == []
    assert len(released) == 1
    assert released[0].consumed_in is None


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
    service.save_bidon(
        payload=BidonPayload(
            identification="p002",
            status="stock",
            consumed_in=None,
            notes="",
        ),
        username="juana",
    )
    service.save_bidon(
        payload=BidonPayload(
            identification="p020",
            status="stock",
            consumed_in=None,
            notes="",
        ),
        username="juana",
    )
    service.save_bidon(
        payload=BidonPayload(
            identification="p120",
            status="stock",
            consumed_in=None,
            notes="",
        ),
        username="juana",
    )

    stock_items = service.search(status="stock")
    consumed_items = service.search(status="consumido")

    assert [item.identification for item in stock_items] == ["B-1001", "P002", "P020", "P120"]
    assert len(consumed_items) == 1
    assert consumed_items[0].consumed_in == "f0975"
    assert service.list_identifications("100") == ["B-1001", "B-1002"]
    assert service.list_identifications("2", status="stock", limit=3) == ["P002", "P020", "P120"]


def test_ensure_default_bidones_creates_p001_to_p200_without_duplicates() -> None:
    session_factory = _session_factory()
    service = BidonService(session_factory)
    service.save_bidon(
        payload=BidonPayload(
            identification="P010",
            status="consumido",
            consumed_in="f0975",
            notes="ya existente",
        ),
        username="juana",
    )

    created = ensure_default_bidones(session_factory)
    all_bidones = service.list_bidones()
    p_bidones = [item for item in all_bidones if item.identification.startswith("P")]
    p010 = next(item for item in p_bidones if item.identification == "P010")

    assert created == 199
    assert len(p_bidones) == 200
    assert p_bidones[0].identification == "P001"
    assert p_bidones[-1].identification == "P200"
    assert p010.status == "consumido"

    created_again = ensure_default_bidones(session_factory)

    assert created_again == 0


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
