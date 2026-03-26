import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.services.bidon_service import BidonPayload, BidonService
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

    window._open_view("producciones.goma_seca")
    back_button = window._entries_by_key["producciones.goma_seca"].back_button
    assert back_button is not None
    assert back_button.text() == "Volver a Producciones"

    window._go_back()
    assert window._current_key == "producciones"


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
