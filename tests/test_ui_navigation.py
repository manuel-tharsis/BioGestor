import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QSpinBox, QDateEdit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.services.bidon_service import BidonPayload, BidonService
from biogestor.services.goma_seca_service import GomaSecaPayload, GomaSecaService
from biogestor.services.solvent_week_metric_service import SolventWeekMetricService
from biogestor.ui.main_window import MainWindow


def _session_factory() -> sessionmaker:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_home_and_navigation_history() -> None:
    _app()
    window = MainWindow("juana", "admin", _session_factory())

    home_buttons = window._entries_by_key["inicio"].widget.findChildren(QPushButton, "homeMenuCard")
    assert len(home_buttons) == 6

    window._open_view("producciones")
    section_buttons = window._entries_by_key["producciones"].widget.findChildren(QPushButton, "sectionMenuCard")
    texts = [button.text() for button in section_buttons]
    assert texts == ["GOMA SECA", "EXTRACCION Y EAL", "DESTILACION"]

    window._open_view("consultas")
    consultas_buttons = window._entries_by_key["consultas"].widget.findChildren(QPushButton, "sectionMenuCard")
    assert [button.text() for button in consultas_buttons] == ["GOMA SECA F1620"]

    window._open_view("producciones.goma_seca")
    back_button = window._entries_by_key["producciones.goma_seca"].back_button
    assert back_button is not None
    assert back_button.text() == "Volver a Consultas"

    assert window._entries_by_key["stock.bidones"].label == "Bidones de Goma Bruta"

    window._go_back()
    assert window._current_key == "consultas"


def test_bidones_visual_search_filters_exact_and_partial_matches() -> None:
    app = _app()
    session_factory = _session_factory()
    service = BidonService(session_factory)
    service.save_bidon(
        payload=BidonPayload("b-1001", "stock", None, ""),
        username="juana",
    )
    service.save_bidon(
        payload=BidonPayload("b-1002", "consumido", "f0975", ""),
        username="juana",
    )

    window = MainWindow("juana", "admin", session_factory)
    bidones_page = window._entries_by_key["stock.bidones"].widget
    search_input = bidones_page.findChild(QLineEdit, "bidonSearchInput")
    status_label = bidones_page.findChild(QLabel, "bidonSearchStatus")
    assert search_input is not None
    assert status_label is not None

    search_input.setText("1002")
    app.processEvents()
    assert "B-1002" in status_label.text()

    search_input.setText("100")
    app.processEvents()
    completer = search_input.completer()
    assert completer is not None
    assert completer.model().stringList() == ["B-1001", "B-1002"]


def test_hexano_page_loads_saved_week_snapshot() -> None:
    _app()
    session_factory = _session_factory()
    service = SolventWeekMetricService(session_factory)
    service.save_snapshot(
        solvent_name="hexano",
        week_start=date(2026, 3, 23),
        purchases_liters=15000,
        stock_liters=11000,
        consumed_liters=3200,
    )

    window = MainWindow("juana", "admin", session_factory)
    hexano_page = window._entries_by_key["stock.disolventes.hexano"].widget
    labels = [label.text() for label in hexano_page.findChildren(QLabel)]
    assert any("Hexano" in text for text in labels)


def test_goma_seca_page_switches_between_entry_and_saved_card() -> None:
    app = _app()
    session_factory = _session_factory()
    service = GomaSecaService(session_factory)
    bidon_service = BidonService(session_factory)
    bidon_service.save_bidon(
        payload=BidonPayload("P001", "stock", None, ""),
        username="juana",
    )
    service.save_production(
        payload=GomaSecaPayload(
            production_date=date.today(),
            lot_code="EG26-088-1",
            finision_number=1,
            kg_produced=1200,
            raw_drum_identification="P001",
            raw_kg_used=1400,
            filter_cleanings=2,
            humidity_percent=8.1,
            day_start_time="07:00",
            top_temperature=81,
            gum_temperature=75,
            vacuum=-0.88,
            distillation_minutes=90,
            observations="ok",
        ),
        username="juana",
    )

    window = MainWindow("juana", "admin", session_factory)
    window._open_view("producciones.goma_seca")
    goma_page = window._entries_by_key["producciones.goma_seca"].widget
    edit_button = goma_page.findChild(QPushButton, "gomaSecaEditButton")
    save_button = goma_page.findChild(QPushButton, "gomaSecaSaveButton")
    validation_label = goma_page.findChild(QLabel, "gomaSecaValidationLabel")
    lote_input = goma_page.findChild(QLineEdit, "gomaSecaLoteInput")
    finision_selector = goma_page.findChild(QSpinBox, "gomaSecaFinisionSelector")
    saved_lot = goma_page.findChild(QLabel, "savedLotValue")

    assert edit_button is not None
    assert save_button is not None
    assert validation_label is not None
    assert lote_input is not None
    assert saved_lot is not None
    assert not edit_button.isHidden()
    assert save_button.isHidden()
    assert "Confirma tu contraseña" in validation_label.text()
    assert lote_input.isReadOnly()
    assert saved_lot.text() == "EG26-088-1"

    # Move to an empty slot and verify the form becomes editable again.
    assert finision_selector is not None
    finision_selector.setValue(2)
    app.processEvents()
    assert edit_button.isHidden()
    assert not save_button.isHidden()
    assert not lote_input.isReadOnly()


def test_consultas_has_lot_selector_button() -> None:
    _app()
    window = MainWindow("juana", "admin", _session_factory())
    window._open_view("consultas.goma_seca_f1620")
    consultas_page = window._entries_by_key["consultas.goma_seca_f1620"].widget
    lot_button = consultas_page.findChild(QPushButton, "consultasLotSelectorButton")
    pdf_button = consultas_page.findChild(QPushButton, "consultasGeneratePdfButton")
    date_inputs = consultas_page.findChildren(QDateEdit)

    assert lot_button is not None
    assert lot_button.text() == "Buscar lote"
    assert pdf_button is not None
    assert pdf_button.text() == "Generar PDF"
    assert len(date_inputs) >= 2
