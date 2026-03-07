from __future__ import annotations

from datetime import date, timedelta
import re

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class GomaSecaWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._week_start = self._start_of_week(date.today())
        self._lote_pattern = re.compile(r"^[A-Z]{2}\d{2}-\d{3}-\d+$")
        self._build_ui()
        self._sync_header()
        self._refresh_lote_suggestion()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        self._prev_week_button = QPushButton("<")
        self._prev_week_button.clicked.connect(self._go_to_previous_week)
        self._next_week_button = QPushButton(">")
        self._next_week_button.clicked.connect(self._go_to_next_week)
        self._week_label = QLabel()
        self._week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._week_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        header.addWidget(self._prev_week_button)
        header.addWidget(self._week_label, stretch=1)
        header.addWidget(self._next_week_button)
        root.addLayout(header)

        form_panel = QFrame()
        form_panel.setFrameShape(QFrame.Shape.StyledPanel)
        form_layout = QFormLayout(form_panel)
        form_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form_layout.setHorizontalSpacing(16)
        form_layout.setVerticalSpacing(10)

        self._fecha_input = QDateEdit()
        self._fecha_input.setCalendarPopup(True)
        self._fecha_input.setDisplayFormat("dd/MM/yyyy")
        self._fecha_input.setDate(self._to_qdate(self._week_start))
        self._fecha_input.dateChanged.connect(self._on_date_changed)
        form_layout.addRow("Fecha:", self._fecha_input)

        lote_row = QVBoxLayout()
        lote_row.setSpacing(4)
        self._lote_input = QLineEdit()
        self._lote_input.setPlaceholderText("EG26-064-2")
        self._lote_input.textEdited.connect(self._validate_lote)
        lote_row.addWidget(self._lote_input)
        self._lote_hint = QLabel()
        self._lote_hint.setStyleSheet("color: #4d7399;")
        lote_row.addWidget(self._lote_hint)
        form_layout.addRow("Lote:", lote_row)

        self._turno_input = QSpinBox()
        self._turno_input.setMinimum(1)
        self._turno_input.setMaximum(9)
        self._turno_input.setValue(1)
        self._turno_input.valueChanged.connect(self._refresh_lote_suggestion)
        form_layout.addRow("N. finision:", self._turno_input)

        self._kg_input = QDoubleSpinBox()
        self._kg_input.setMaximum(100000)
        self._kg_input.setDecimals(2)
        self._kg_input.setSuffix(" kg")
        self._kg_input.setValue(0.0)
        form_layout.addRow("Kg producidos:", self._kg_input)

        self._humedad_input = QDoubleSpinBox()
        self._humedad_input.setMaximum(100)
        self._humedad_input.setDecimals(2)
        self._humedad_input.setSuffix(" %")
        self._humedad_input.setSingleStep(0.1)
        self._humedad_input.setValue(8.5)
        form_layout.addRow("Humedad sugerida:", self._humedad_input)

        self._observaciones_input = QTextEdit()
        self._observaciones_input.setPlaceholderText("Observaciones de la semana...")
        self._observaciones_input.setMinimumHeight(90)
        form_layout.addRow("Observaciones:", self._observaciones_input)

        root.addWidget(form_panel)
        root.addStretch(1)

    def _go_to_previous_week(self) -> None:
        self._week_start -= timedelta(days=7)
        self._sync_header()
        self._fecha_input.setDate(self._to_qdate(self._week_start))
        self._refresh_lote_suggestion()

    def _go_to_next_week(self) -> None:
        self._week_start += timedelta(days=7)
        self._sync_header()
        self._fecha_input.setDate(self._to_qdate(self._week_start))
        self._refresh_lote_suggestion()

    def _sync_header(self) -> None:
        week_end = self._week_start + timedelta(days=6)
        iso_week = self._week_start.isocalendar().week
        label = (
            f"Semana {iso_week} "
            f"({self._week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})"
        )
        self._week_label.setText(label)

    def _on_date_changed(self, _value: QDate | None = None) -> None:
        selected = self._fecha_input.date().toPython()
        self._week_start = self._start_of_week(selected)
        self._sync_header()
        self._refresh_lote_suggestion()

    def _refresh_lote_suggestion(self, _value: int | None = None) -> None:
        selected_date = self._fecha_input.date().toPython()
        year = selected_date.strftime("%y")
        day_of_year = selected_date.timetuple().tm_yday
        suggestion = f"EG{year}-{day_of_year:03d}-{self._turno_input.value()}"
        self._lote_hint.setText(f"Sugerido automaticamente: {suggestion}")
        if not self._lote_input.text().strip():
            self._lote_input.setText(suggestion)
            self._validate_lote()

    def _validate_lote(self, _value: str | None = None) -> None:
        lote = self._lote_input.text().strip().upper()
        self._lote_input.setText(lote)
        if not lote:
            self._lote_input.setStyleSheet("")
            return
        if self._lote_pattern.match(lote):
            self._lote_input.setStyleSheet("border: 1px solid #4f8a5b;")
        else:
            self._lote_input.setStyleSheet("border: 1px solid #b64f4f;")

    @staticmethod
    def _start_of_week(value: date) -> date:
        return value - timedelta(days=value.weekday())

    @staticmethod
    def _to_qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
