from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtGui import QPageSize, QPainter, QPdfWriter
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.goma_seca_production import GomaSecaProduction
from biogestor.services.goma_seca_service import GomaSecaService


class ConsultasWidget(QWidget):
    _DEFAULT_START_DATE = date(2026, 1, 1)

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._goma_seca_service = GomaSecaService(session_factory)
        self._selected_lot = ""
        self._current_items: list[GomaSecaProduction] = []
        self._build_ui()
        self._refresh_results()

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._refresh_results()
        super().showEvent(event)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        filters = QFrame()
        filters.setObjectName("panelCard")
        filters_layout = QFormLayout(filters)

        self._date_from_input = QDateEdit()
        self._date_from_input.setCalendarPopup(True)
        self._date_from_input.setDisplayFormat("dd/MM/yyyy")
        self._date_from_input.setDate(self._to_qdate(self._DEFAULT_START_DATE))
        filters_layout.addRow("Desde:", self._date_from_input)

        self._date_to_input = QDateEdit()
        self._date_to_input.setCalendarPopup(True)
        self._date_to_input.setDisplayFormat("dd/MM/yyyy")
        self._date_to_input.setDate(self._to_qdate(date.today()))
        filters_layout.addRow("Hasta:", self._date_to_input)

        self._lot_selector_button = QPushButton("Buscar lote")
        self._lot_selector_button.setObjectName("consultasLotSelectorButton")
        self._lot_selector_button.clicked.connect(self._open_lot_selector)
        filters_layout.addRow("Lote:", self._lot_selector_button)

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
        production_title = QLabel("Goma seca F1620")
        production_title.setObjectName("sectionTitle")
        production_layout.addWidget(production_title)

        self._summary_label = QLabel()
        self._summary_label.setStyleSheet("color: #486581;")
        self._summary_label.setWordWrap(True)
        production_layout.addWidget(self._summary_label)

        self._production_table = QTableWidget(0, 7)
        self._production_table.setHorizontalHeaderLabels(
            [
                "Fecha",
                "Lote",
                "Finisión",
                "N.º bidón",
                "Kg consumidos",
                "Kg producidos",
                "Rendimiento",
            ]
        )
        self._production_table.verticalHeader().setVisible(False)
        production_layout.addWidget(self._production_table)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._pdf_button = QPushButton("Generar PDF")
        self._pdf_button.setObjectName("consultasGeneratePdfButton")
        self._pdf_button.clicked.connect(self._export_pdf)
        footer.addWidget(self._pdf_button)
        production_layout.addLayout(footer)
        root.addWidget(production_panel, stretch=1)

    def _refresh_results(self) -> None:
        date_from = self._date_from_input.date().toPython()
        date_to = self._date_to_input.date().toPython()
        self._current_items = self._goma_seca_service.search(
            date_from=date_from,
            date_to=date_to,
            lot_contains=self._selected_lot,
        )
        self._populate_productions(self._current_items)
        self._update_summary()

    def _populate_productions(self, items: list[GomaSecaProduction]) -> None:
        self._production_table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.production_date.strftime("%d/%m/%Y"),
                item.lot_code,
                str(item.finision_number),
                item.raw_drum_identification,
                f"{item.raw_kg_used:.2f}",
                f"{item.kg_produced:.2f}",
                "-" if item.raw_kg_used <= 0 else f"{item.kg_produced / item.raw_kg_used:.3f}",
            ]
            for column, value in enumerate(values):
                self._production_table.setItem(row, column, QTableWidgetItem(value))
        self._production_table.resizeColumnsToContents()

    def _update_summary(self) -> None:
        date_from = self._date_from_input.date().toPython().strftime("%d/%m/%Y")
        date_to = self._date_to_input.date().toPython().strftime("%d/%m/%Y")
        lot_text = self._selected_lot if self._selected_lot else "Todos los lotes"
        self._summary_label.setText(
            f"Período: {date_from} - {date_to}. Lote: {lot_text}. Registros: {len(self._current_items)}."
        )

    def _clear_filters(self) -> None:
        self._date_from_input.setDate(self._to_qdate(self._DEFAULT_START_DATE))
        self._date_to_input.setDate(self._to_qdate(date.today()))
        self._selected_lot = ""
        self._sync_lot_button()
        self._refresh_results()

    def _open_lot_selector(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Seleccionar lote")
        dialog.resize(420, 480)
        layout = QVBoxLayout(dialog)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Filtrar lotes...")
        layout.addWidget(search_input)

        list_widget = QListWidget()
        list_widget.setObjectName("consultasLotList")
        layout.addWidget(list_widget, stretch=1)

        actions = QHBoxLayout()
        clear_button = QPushButton("Todos")
        select_button = QPushButton("Seleccionar")
        actions.addWidget(clear_button)
        actions.addStretch(1)
        actions.addWidget(select_button)
        layout.addLayout(actions)

        lots = self._goma_seca_service.list_lots(
            date_from=self._date_from_input.date().toPython(),
            date_to=self._date_to_input.date().toPython(),
        )

        def populate(filter_text: str = "") -> None:
            current_text = filter_text.strip().upper()
            list_widget.clear()
            for lot in lots:
                if current_text and current_text not in lot:
                    continue
                list_widget.addItem(QListWidgetItem(lot))

        def apply_selection() -> None:
            current_item = list_widget.currentItem()
            if current_item is None:
                return
            self._selected_lot = current_item.text()
            self._sync_lot_button()
            dialog.accept()
            self._refresh_results()

        def clear_selection() -> None:
            self._selected_lot = ""
            self._sync_lot_button()
            dialog.accept()
            self._refresh_results()

        search_input.textChanged.connect(populate)
        list_widget.itemDoubleClicked.connect(lambda _item: apply_selection())
        select_button.clicked.connect(apply_selection)
        clear_button.clicked.connect(clear_selection)
        populate(self._selected_lot)
        dialog.exec()

    def _sync_lot_button(self) -> None:
        if self._selected_lot:
            self._lot_selector_button.setText(f"Lote: {self._selected_lot}")
        else:
            self._lot_selector_button.setText("Buscar lote")

    def _export_pdf(self) -> None:
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar consulta como PDF",
            "consulta_goma_seca_f1620.pdf",
            "PDF (*.pdf)",
        )
        if not file_path:
            return

        writer = QPdfWriter(file_path)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        writer.setResolution(144)
        painter = QPainter(writer)

        margin = 80
        line_height = 28
        y = margin

        def draw_line(text: str, *, bold: bool = False) -> None:
            nonlocal y
            font = painter.font()
            font.setBold(bold)
            font.setPointSize(10 if not bold else 12)
            painter.setFont(font)
            painter.drawText(margin, y, text)
            y += line_height
            if y > writer.height() - margin:
                writer.newPage()
                y = margin

        draw_line("Consulta de goma seca F1620", bold=True)
        draw_line(
            f"Período: {self._date_from_input.date().toPython().strftime('%d/%m/%Y')} - "
            f"{self._date_to_input.date().toPython().strftime('%d/%m/%Y')}"
        )
        draw_line(f"Lote: {self._selected_lot or 'Todos los lotes'}")
        draw_line(f"Registros: {len(self._current_items)}")
        y += 10
        draw_line("Fecha | Lote | Finisión | N.º bidón | Kg consumidos | Kg producidos | Rendimiento", bold=True)

        for item in self._current_items:
            draw_line(
                " | ".join(
                    [
                        item.production_date.strftime("%d/%m/%Y"),
                        item.lot_code,
                        str(item.finision_number),
                        item.raw_drum_identification,
                        f"{item.raw_kg_used:.2f}",
                        f"{item.kg_produced:.2f}",
                        "-" if item.raw_kg_used <= 0 else f"{item.kg_produced / item.raw_kg_used:.3f}",
                    ]
                )
            )

        painter.end()

    @staticmethod
    def _to_qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
