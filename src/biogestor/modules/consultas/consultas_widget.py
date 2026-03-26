from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.services.bidon_service import BidonService
from biogestor.services.goma_seca_service import GomaSecaService


class ConsultasWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._goma_seca_service = GomaSecaService(session_factory)
        self._bidon_service = BidonService(session_factory)
        self._build_ui()
        self._refresh_results()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        filters = QFrame()
        filters.setObjectName("panelCard")
        filters_layout = QFormLayout(filters)

        self._week_input = QDateEdit()
        self._week_input.setCalendarPopup(True)
        self._week_input.setDisplayFormat("dd/MM/yyyy")
        self._week_input.setDate(self._to_qdate(self._start_of_week(date.today())))
        filters_layout.addRow("Semana:", self._week_input)

        self._lot_filter = QLineEdit()
        self._lot_filter.setPlaceholderText("Buscar lote")
        filters_layout.addRow("Lote:", self._lot_filter)

        self._bidon_filter = QLineEdit()
        self._bidon_filter.setPlaceholderText("Buscar bidon")
        filters_layout.addRow("Bidon:", self._bidon_filter)

        actions = QHBoxLayout()
        apply_button = QPushButton("Consultar")
        apply_button.clicked.connect(self._refresh_results)
        clear_button = QPushButton("Limpiar")
        clear_button.clicked.connect(self._clear_filters)
        actions.addWidget(apply_button)
        actions.addWidget(clear_button)
        filters_layout.addRow("", actions)
        root.addWidget(filters)

        production_panel = QFrame()
        production_panel.setObjectName("panelCard")
        production_layout = QVBoxLayout(production_panel)
        production_title = QLabel("Producciones de goma seca")
        production_title.setObjectName("sectionTitle")
        production_layout.addWidget(production_title)

        self._production_table = QTableWidget(0, 5)
        self._production_table.setHorizontalHeaderLabels(
            ["Fecha", "Lote", "Finision", "Kg", "Humedad"]
        )
        self._production_table.verticalHeader().setVisible(False)
        production_layout.addWidget(self._production_table)
        root.addWidget(production_panel, stretch=1)

        bidones_panel = QFrame()
        bidones_panel.setObjectName("panelCard")
        bidones_layout = QVBoxLayout(bidones_panel)
        bidones_title = QLabel("Bidones")
        bidones_title.setObjectName("sectionTitle")
        bidones_layout.addWidget(bidones_title)

        self._bidones_table = QTableWidget(0, 3)
        self._bidones_table.setHorizontalHeaderLabels(["Identificacion", "Estado", "Consumo"])
        self._bidones_table.verticalHeader().setVisible(False)
        bidones_layout.addWidget(self._bidones_table)
        root.addWidget(bidones_panel, stretch=1)

    def _refresh_results(self) -> None:
        week_start = self._start_of_week(self._week_input.date().toPython())
        productions = self._goma_seca_service.search(
            week_start=week_start,
            lot_contains=self._lot_filter.text(),
        )
        bidones = self._bidon_service.search(
            identification_contains=self._bidon_filter.text(),
            status="todos",
        )
        self._populate_productions(productions)
        self._populate_bidones(bidones)

    def _populate_productions(self, items) -> None:
        self._production_table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.production_date.strftime("%d/%m/%Y"),
                item.lot_code,
                str(item.finision_number),
                f"{item.kg_produced:.2f}",
                f"{item.humidity_percent:.2f} %",
            ]
            for column, value in enumerate(values):
                self._production_table.setItem(row, column, QTableWidgetItem(value))
        self._production_table.resizeColumnsToContents()

    def _populate_bidones(self, items) -> None:
        self._bidones_table.setRowCount(len(items))
        for row, item in enumerate(items):
            consumo = "-"
            if item.status == "consumido":
                consumo = (item.consumed_in or "").upper() or "-"
            values = [
                item.identification,
                "En stock" if item.status == "stock" else "Consumido",
                consumo,
            ]
            for column, value in enumerate(values):
                self._bidones_table.setItem(row, column, QTableWidgetItem(value))
        self._bidones_table.resizeColumnsToContents()

    def _clear_filters(self) -> None:
        self._week_input.setDate(self._to_qdate(self._start_of_week(date.today())))
        self._lot_filter.clear()
        self._bidon_filter.clear()
        self._refresh_results()

    @staticmethod
    def _start_of_week(value: date) -> date:
        return value - timedelta(days=value.weekday())

    @staticmethod
    def _to_qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
