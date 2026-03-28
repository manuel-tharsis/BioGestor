from __future__ import annotations

from datetime import date, timedelta
import re

from PySide6.QtCore import QDate, Qt, QTime, Signal
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCompleter,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.goma_seca_production import GomaSecaProduction
from biogestor.services.auth_service import AuthService
from biogestor.services.bidon_service import BidonService
from biogestor.services.goma_seca_service import GomaSecaPayload, GomaSecaService


class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class NoWheelTimeEdit(QTimeEdit):
    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class GomaSecaWidget(QWidget):
    production_saved = Signal(str)

    _DAY_NAMES = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    def __init__(self, session_factory: sessionmaker[Session], username: str) -> None:
        super().__init__()
        self._username = username
        self._service = GomaSecaService(session_factory)
        self._auth_service = AuthService(session_factory)
        self._bidon_service = BidonService(session_factory)
        self._selected_date = date.today()
        self._selected_finision = 1
        self._current_record: GomaSecaProduction | None = None
        self._is_editing_existing = False
        self._lote_pattern = re.compile(r"^[A-Z]{2}\d{2}-\d{3}-\d+$")
        self._build_ui()
        self._sync_headers()
        self._sync_bidon_suggestions()
        self._load_slot()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        week_header = QHBoxLayout()
        self._prev_week_button = QPushButton("<")
        self._prev_week_button.clicked.connect(self._go_to_previous_week)
        self._next_week_button = QPushButton(">")
        self._next_week_button.clicked.connect(self._go_to_next_week)
        self._week_label = QLabel()
        self._week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._week_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        week_header.addWidget(self._prev_week_button)
        week_header.addWidget(self._week_label, stretch=1)
        week_header.addWidget(self._next_week_button)
        root.addLayout(week_header)

        day_header = QHBoxLayout()
        self._prev_day_button = QPushButton("<")
        self._prev_day_button.clicked.connect(self._go_to_previous_day)
        self._next_day_button = QPushButton(">")
        self._next_day_button.clicked.connect(self._go_to_next_day)
        self._day_label = QLabel()
        self._day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._day_label.setStyleSheet("font-weight: 700; font-size: 15px;")
        day_header.addWidget(self._prev_day_button)
        day_header.addWidget(self._day_label, stretch=1)
        day_header.addWidget(self._next_day_button)
        root.addLayout(day_header)

        selector_panel = QFrame()
        selector_panel.setObjectName("panelCard")
        selector_layout = QHBoxLayout(selector_panel)
        selector_layout.setContentsMargins(16, 12, 16, 12)
        selector_layout.setSpacing(12)
        selector_label = QLabel("Finisión")
        selector_label.setStyleSheet("font-weight: 700; color: #334e68;")
        selector_layout.addWidget(selector_label)

        self._finision_selector = NoWheelSpinBox()
        self._finision_selector.setObjectName("gomaSecaFinisionSelector")
        self._finision_selector.setMinimum(1)
        self._finision_selector.setMaximum(self._service.MAX_FINISION)
        self._finision_selector.setValue(1)
        self._finision_selector.valueChanged.connect(self._on_finision_changed)
        selector_layout.addWidget(self._finision_selector)

        selector_layout.addStretch(1)

        self._edit_button = QPushButton("Editar")
        self._edit_button.setObjectName("gomaSecaEditButton")
        self._edit_button.setVisible(False)
        self._edit_button.clicked.connect(self._toggle_edit_mode)
        edit_icon = QIcon.fromTheme("document-edit")
        if edit_icon.isNull():
            edit_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self._edit_button.setIcon(edit_icon)
        selector_layout.addWidget(self._edit_button)
        root.addWidget(selector_panel)

        self._form_panel = QFrame()
        self._form_panel.setObjectName("panelCard")
        form_root = QVBoxLayout(self._form_panel)
        form_root.setContentsMargins(16, 16, 16, 16)
        form_root.setSpacing(14)

        self._content_stack = QStackedWidget()
        self._entry_view = self._build_entry_view()
        self._saved_view = self._build_saved_view()
        self._content_stack.addWidget(self._entry_view)
        self._content_stack.addWidget(self._saved_view)
        form_root.addWidget(self._content_stack)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        self._validation_label = QLabel()
        self._validation_label.setObjectName("gomaSecaValidationLabel")
        self._validation_label.setWordWrap(True)
        footer.addWidget(self._validation_label, stretch=1)

        self._save_button = QPushButton("Guardar")
        self._save_button.setObjectName("gomaSecaSaveButton")
        self._save_button.clicked.connect(self._save)
        footer.addWidget(self._save_button, alignment=Qt.AlignmentFlag.AlignRight)
        form_root.addLayout(footer)
        root.addWidget(self._form_panel)

        records_panel = QFrame()
        records_panel.setObjectName("panelCard")
        records_layout = QVBoxLayout(records_panel)
        records_title = QLabel("RESUMEN DE LA SEMANA")
        records_title.setObjectName("sectionTitle")
        records_layout.addWidget(records_title)

        self._records_table = QTableWidget(0, 7)
        self._records_table.setHorizontalHeaderLabels(
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
        self._records_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._records_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._records_table.verticalHeader().setVisible(False)
        records_layout.addWidget(self._records_table)
        root.addWidget(records_panel, stretch=1)

    def _build_entry_view(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        self._production_group = self._build_production_group()
        self._consumption_group = self._build_consumption_group()
        self._parameters_group = self._build_parameters_group()
        layout.addWidget(self._production_group)
        layout.addWidget(self._consumption_group)
        layout.addWidget(self._parameters_group)
        return container

    def _build_saved_view(self) -> QWidget:
        container = QFrame()
        container.setObjectName("gomaSecaSavedCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(self._build_saved_production_group())
        layout.addWidget(self._build_saved_group("CONSUMO", [
            ("N.º bidón de goma bruta", "savedBidonValue"),
            ("KG Goma Bruta", "savedKgRawValue"),
        ]))
        layout.addWidget(self._build_saved_group("PARÁMETROS DE LA FINISIÓN", [
            ("N.º limpiezas del filtro", "savedFilterCleaningsValue"),
            ("Humedad", "savedHumidityValue"),
            ("Hora inicio día", "savedDayStartValue"),
            ("Temperatura parte alta", "savedTopTempValue"),
            ("Temperatura goma", "savedGumTempValue"),
            ("Vacío", "savedVacuumValue"),
            ("Tiempo destilación", "savedDistillationValue"),
            ("Observaciones", "savedObservationsValue"),
        ]))
        return container

    def _build_saved_production_group(self) -> QGroupBox:
        group = QGroupBox("PRODUCCION")
        layout = QFormLayout(group)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        saved_lot = QLabel("-")
        saved_lot.setObjectName("savedLotValue")
        saved_lot.setWordWrap(True)
        saved_lot.setStyleSheet(
            "background: #f8fbff; border: 1px solid #d9e2ec; border-radius: 10px; padding: 8px 10px;"
        )
        layout.addRow("Lote:", saved_lot)

        finision_row = QHBoxLayout()
        finision_row.setContentsMargins(0, 0, 0, 0)
        finision_row.setSpacing(12)
        saved_finision = QLabel("-")
        saved_finision.setObjectName("savedFinisionValue")
        saved_finision.setStyleSheet(
            "background: #f8fbff; border: 1px solid #d9e2ec; border-radius: 10px; padding: 8px 10px;"
        )
        finision_row.addWidget(saved_finision)
        layout.addRow("Finisión:", finision_row)

        saved_kg = QLabel("-")
        saved_kg.setObjectName("savedKgProducedValue")
        saved_kg.setWordWrap(True)
        saved_kg.setStyleSheet(
            "background: #f8fbff; border: 1px solid #d9e2ec; border-radius: 10px; padding: 8px 10px;"
        )
        layout.addRow("KG producidos:", saved_kg)
        return group

    def _build_saved_group(self, title: str, rows: list[tuple[str, str]]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QFormLayout(group)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)
        for label_text, object_name in rows:
            value_label = QLabel("-")
            value_label.setObjectName(object_name)
            value_label.setWordWrap(True)
            value_label.setStyleSheet(
                "background: #f8fbff; border: 1px solid #d9e2ec; border-radius: 10px; padding: 8px 10px;"
            )
            layout.addRow(f"{label_text}:", value_label)
        return group

    def _build_production_group(self) -> QGroupBox:
        group = QGroupBox("PRODUCCION")
        layout = QFormLayout(group)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        lote_row = QVBoxLayout()
        lote_row.setSpacing(4)
        self._lote_input = QLineEdit()
        self._lote_input.setObjectName("gomaSecaLoteInput")
        self._lote_input.setPlaceholderText("EG26-064-1")
        self._lote_input.textEdited.connect(self._validate_form)
        lote_row.addWidget(self._lote_input)

        self._lote_hint = QLabel()
        self._lote_hint.setStyleSheet("color: #4d7399;")
        lote_row.addWidget(self._lote_hint)
        layout.addRow("Lote:", lote_row)

        self._finision_input = NoWheelSpinBox()
        self._finision_input.setMinimum(1)
        self._finision_input.setMaximum(self._service.MAX_FINISION)
        self._finision_input.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._finision_input.setReadOnly(True)
        finision_row = QHBoxLayout()
        finision_row.setContentsMargins(0, 0, 0, 0)
        finision_row.setSpacing(12)
        finision_row.addWidget(self._finision_input)
        layout.addRow("Finisión:", finision_row)

        self._kg_input = NoWheelDoubleSpinBox()
        self._kg_input.setMaximum(100000)
        self._kg_input.setDecimals(2)
        self._kg_input.setSuffix(" kg")
        self._kg_input.valueChanged.connect(self._validate_form)
        layout.addRow("KG producidos:", self._kg_input)
        return group

    def _build_consumption_group(self) -> QGroupBox:
        group = QGroupBox("CONSUMO")
        layout = QFormLayout(group)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self._raw_drum_input = QLineEdit()
        self._raw_drum_input.setPlaceholderText("P001")
        self._raw_drum_input.textEdited.connect(self._on_bidon_text_changed)
        self._bidon_completer = QCompleter([])
        self._bidon_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._bidon_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._raw_drum_input.setCompleter(self._bidon_completer)
        layout.addRow("N.º bidón de goma bruta:", self._raw_drum_input)

        self._raw_kg_input = NoWheelDoubleSpinBox()
        self._raw_kg_input.setMaximum(100000)
        self._raw_kg_input.setDecimals(2)
        self._raw_kg_input.setSuffix(" kg")
        self._raw_kg_input.valueChanged.connect(self._validate_form)
        layout.addRow("KG Goma Bruta:", self._raw_kg_input)
        return group

    def _build_parameters_group(self) -> QGroupBox:
        group = QGroupBox("PARÁMETROS DE LA FINISIÓN")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(10)

        self._filter_cleanings_input = NoWheelSpinBox()
        self._filter_cleanings_input.setMaximum(50)
        self._filter_cleanings_input.valueChanged.connect(self._validate_form)
        self._add_grid_field(layout, 0, "N.º limpiezas del filtro:", self._filter_cleanings_input)

        self._humidity_input = NoWheelDoubleSpinBox()
        self._humidity_input.setMaximum(100)
        self._humidity_input.setDecimals(2)
        self._humidity_input.setSuffix(" %")
        self._humidity_input.setSingleStep(0.1)
        self._add_grid_field(layout, 0, "Humedad:", self._humidity_input, column=2)

        self._day_start_input = NoWheelTimeEdit()
        self._day_start_input.setDisplayFormat("HH:mm")
        self._day_start_input.setTime(QTime(7, 0))
        self._add_grid_field(layout, 1, "Hora inicio día:", self._day_start_input)

        self._top_temperature_input = NoWheelDoubleSpinBox()
        self._top_temperature_input.setRange(-50, 300)
        self._top_temperature_input.setDecimals(2)
        self._top_temperature_input.setSuffix(" C")
        self._add_grid_field(layout, 1, "Temperatura parte alta:", self._top_temperature_input, column=2)

        self._gum_temperature_input = NoWheelDoubleSpinBox()
        self._gum_temperature_input.setRange(-50, 300)
        self._gum_temperature_input.setDecimals(2)
        self._gum_temperature_input.setSuffix(" C")
        self._add_grid_field(layout, 2, "Temperatura goma:", self._gum_temperature_input)

        self._vacuum_input = NoWheelDoubleSpinBox()
        self._vacuum_input.setRange(-5, 5)
        self._vacuum_input.setDecimals(3)
        self._vacuum_input.setSingleStep(0.01)
        self._vacuum_input.setSuffix(" bar")
        self._add_grid_field(layout, 2, "Vacío:", self._vacuum_input, column=2)

        self._distillation_input = NoWheelSpinBox()
        self._distillation_input.setMaximum(1440)
        self._distillation_input.setSuffix(" min")
        self._add_grid_field(layout, 3, "Tiempo destilación:", self._distillation_input)

        self._observaciones_input = QTextEdit()
        self._observaciones_input.setPlaceholderText("Observaciones...")
        self._observaciones_input.setMaximumHeight(80)
        layout.addWidget(QLabel("Observaciones:"), 4, 0)
        layout.addWidget(self._observaciones_input, 4, 1, 1, 3)
        return group

    def _add_grid_field(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        widget: QWidget,
        *,
        column: int = 0,
    ) -> None:
        layout.addWidget(QLabel(label), row, column)
        layout.addWidget(widget, row, column + 1)

    def _go_to_previous_week(self) -> None:
        self._selected_date -= timedelta(days=7)
        self._sync_headers()
        self._load_slot()

    def _go_to_next_week(self) -> None:
        self._selected_date += timedelta(days=7)
        self._sync_headers()
        self._load_slot()

    def _go_to_previous_day(self) -> None:
        self._selected_date -= timedelta(days=1)
        self._sync_headers()
        self._load_slot()

    def _go_to_next_day(self) -> None:
        self._selected_date += timedelta(days=1)
        self._sync_headers()
        self._load_slot()

    def _on_finision_changed(self, value: int) -> None:
        self._selected_finision = value
        self._load_slot()

    def _sync_headers(self) -> None:
        week_start = self._start_of_week(self._selected_date)
        self._week_label.setText(f"Semana {week_start.isocalendar().week}")
        day_name = self._DAY_NAMES[self._selected_date.weekday()]
        self._day_label.setText(f"{day_name} {self._selected_date.strftime('%d/%m/%Y')}")
        self._finision_input.setValue(self._selected_finision)

    def _sync_bidon_suggestions(self) -> None:
        suggestions = self._production_bidones_suggestions()
        self._bidon_completer.model().setStringList(suggestions)  # type: ignore[union-attr]

    def _on_bidon_text_changed(self, _value: str) -> None:
        self._raw_drum_input.setText(self._raw_drum_input.text().strip().upper())
        suggestions = self._production_bidones_suggestions(self._raw_drum_input.text())
        self._bidon_completer.model().setStringList(suggestions)  # type: ignore[union-attr]
        self._validate_form()

    def _production_bidones_suggestions(self, query: str | None = None) -> list[str]:
        suggestions = self._bidon_service.list_identifications(
            query,
            status="stock",
            limit=12,
        )
        current_bidon = self._raw_drum_input.text().strip().upper()
        if self._is_editing_existing and current_bidon:
            suggestions = [current_bidon, *[item for item in suggestions if item != current_bidon]]
        return suggestions

    def _load_slot(self) -> None:
        self._current_record = self._service.get_slot(self._selected_date, self._selected_finision)
        self._is_editing_existing = False
        self._sync_headers()
        self._sync_bidon_suggestions()
        self._refresh_form_for_slot()
        self._refresh_week_summary()

    def _refresh_form_for_slot(self) -> None:
        self._edit_button.setVisible(self._current_record is not None and not self._is_editing_existing)
        self._edit_button.setText("Editar")
        if self._current_record is None:
            self._populate_empty_form()
            self._set_form_editable(True)
            self._content_stack.setCurrentWidget(self._entry_view)
            self._save_button.setVisible(True)
            self._validate_form()
            return

        self._populate_form_from_record(self._current_record)
        if self._is_editing_existing:
            self._content_stack.setCurrentWidget(self._entry_view)
            self._set_form_editable(True)
            self._save_button.setVisible(True)
            self._validate_form()
        else:
            self._populate_saved_view(self._current_record)
            self._content_stack.setCurrentWidget(self._saved_view)
            self._set_form_editable(False)
            self._save_button.setVisible(False)
            self._set_validation_message(
                "Datos guardados para este día y finisión. Confirma tu contraseña para editar.",
                error=False,
            )

    def _populate_empty_form(self) -> None:
        self._kg_input.setValue(0.0)
        self._raw_drum_input.clear()
        self._raw_kg_input.setValue(0.0)
        self._filter_cleanings_input.setValue(0)
        self._humidity_input.setValue(8.5)
        self._day_start_input.setTime(QTime(7, 0))
        self._top_temperature_input.setValue(0.0)
        self._gum_temperature_input.setValue(0.0)
        self._vacuum_input.setValue(0.0)
        self._distillation_input.setValue(0)
        self._observaciones_input.clear()
        self._refresh_lote_suggestion(force=True)

    def _populate_form_from_record(self, record: GomaSecaProduction) -> None:
        self._lote_input.setText(record.lot_code)
        self._finision_input.setValue(record.finision_number)
        self._kg_input.setValue(record.kg_produced)
        self._raw_drum_input.setText(record.raw_drum_identification)
        self._raw_kg_input.setValue(record.raw_kg_used)
        self._filter_cleanings_input.setValue(record.filter_cleanings)
        self._humidity_input.setValue(record.humidity_percent)
        self._day_start_input.setTime(self._time_from_text(record.day_start_time))
        self._top_temperature_input.setValue(record.top_temperature)
        self._gum_temperature_input.setValue(record.gum_temperature)
        self._vacuum_input.setValue(record.vacuum)
        self._distillation_input.setValue(record.distillation_minutes)
        self._observaciones_input.setPlainText(record.observations)
        self._refresh_lote_suggestion(force=False)

    def _populate_saved_view(self, record: GomaSecaProduction) -> None:
        self.findChild(QLabel, "savedLotValue").setText(record.lot_code)
        self.findChild(QLabel, "savedFinisionValue").setText(str(record.finision_number))
        self.findChild(QLabel, "savedKgProducedValue").setText(f"{record.kg_produced:.2f} kg")
        self.findChild(QLabel, "savedBidonValue").setText(record.raw_drum_identification)
        self.findChild(QLabel, "savedKgRawValue").setText(f"{record.raw_kg_used:.2f} kg")
        self.findChild(QLabel, "savedFilterCleaningsValue").setText(str(record.filter_cleanings))
        self.findChild(QLabel, "savedHumidityValue").setText(f"{record.humidity_percent:.2f} %")
        self.findChild(QLabel, "savedDayStartValue").setText(record.day_start_time)
        self.findChild(QLabel, "savedTopTempValue").setText(f"{record.top_temperature:.2f} C")
        self.findChild(QLabel, "savedGumTempValue").setText(f"{record.gum_temperature:.2f} C")
        self.findChild(QLabel, "savedVacuumValue").setText(f"{record.vacuum:.3f} bar")
        self.findChild(QLabel, "savedDistillationValue").setText(f"{record.distillation_minutes} min")
        self.findChild(QLabel, "savedObservationsValue").setText(record.observations or "-")

    def _refresh_lote_suggestion(self, *, force: bool) -> None:
        suggestion = self._suggested_lote()
        self._lote_hint.setText(f"Sugerido automáticamente: {suggestion}")
        if force:
            self._lote_input.setText(suggestion)
        elif not self._current_record and not self._lote_input.text().strip():
            self._lote_input.setText(suggestion)

    def _suggested_lote(self) -> str:
        year = self._selected_date.strftime("%y")
        day_of_year = self._selected_date.timetuple().tm_yday
        return f"EG{year}-{day_of_year:03d}-{self._selected_finision}"

    def _toggle_edit_mode(self) -> None:
        if self._current_record is None:
            return

        password, accepted = QInputDialog.getText(
            self,
            "Confirmar contraseña",
            "Introduce tu contraseña para editar este registro:",
            QLineEdit.EchoMode.Password,
        )
        if not accepted:
            return
        if not self._auth_service.confirm_password(self._username, password):
            self._set_validation_message("Contraseña incorrecta. No se ha habilitado la edición.", error=True)
            return

        self._is_editing_existing = True
        self._edit_button.setText("Cancelar")
        self._refresh_form_for_slot()

    def _set_form_editable(self, editable: bool) -> None:
        self._lote_input.setReadOnly(not editable)
        self._raw_drum_input.setReadOnly(not editable)
        self._kg_input.setEnabled(editable)
        self._raw_kg_input.setEnabled(editable)
        self._filter_cleanings_input.setEnabled(editable)
        self._humidity_input.setEnabled(editable)
        self._day_start_input.setEnabled(editable)
        self._top_temperature_input.setEnabled(editable)
        self._gum_temperature_input.setEnabled(editable)
        self._vacuum_input.setEnabled(editable)
        self._distillation_input.setEnabled(editable)
        self._observaciones_input.setReadOnly(not editable)
        self._finision_input.setEnabled(False)

    def _validate_form(self, _value: object | None = None) -> None:
        if self._current_record is not None and not self._is_editing_existing:
            self._save_button.setEnabled(False)
            return

        lote = self._lote_input.text().strip().upper()
        self._lote_input.setText(lote)
        record_id = self._current_record.id if self._is_editing_existing and self._current_record else None

        if not self._lote_pattern.match(lote):
            self._set_validation_message(
                "Lote erróneo. Debe seguir el formato EG26-064-1.",
                error=True,
            )
            self._save_button.setEnabled(False)
            return

        is_valid, message = self._service.validate_lot(
            lot_code=lote,
            production_date=self._selected_date,
            finision_number=self._selected_finision,
            record_id=record_id,
        )
        if not is_valid:
            self._set_validation_message(message, error=True)
            self._save_button.setEnabled(False)
            return

        if not self._raw_drum_input.text().strip():
            self._set_validation_message("Indica el número de bidón de goma bruta.", error=True)
            self._save_button.setEnabled(False)
            return

        if not self._is_valid_raw_drum(self._raw_drum_input.text()):
            self._set_validation_message(
                "El bidón debe coincidir con un bidón de goma bruta disponible.",
                error=True,
            )
            self._save_button.setEnabled(False)
            return

        if self._kg_input.value() <= 0:
            self._set_validation_message("Indica los kg producidos.", error=True)
            self._save_button.setEnabled(False)
            return

        if self._raw_kg_input.value() <= 0:
            self._set_validation_message("Indica los kg consumidos de goma bruta.", error=True)
            self._save_button.setEnabled(False)
            return

        self._set_validation_message(message, error=False)
        self._save_button.setEnabled(True)

    def _set_validation_message(self, message: str, *, error: bool) -> None:
        self._validation_label.setText(message)
        if error:
            self._validation_label.setStyleSheet(
                "color: #b42318; font-weight: 700; padding: 6px 0;"
            )
        else:
            self._validation_label.setStyleSheet(
                "color: #166534; font-weight: 700; padding: 6px 0;"
            )
        self._validation_label.setVisible(True)

    def _is_valid_raw_drum(self, value: str) -> bool:
        normalized = value.strip().upper()
        if not normalized:
            return False
        available = self._bidon_service.list_identifications(normalized, status="stock")
        if normalized in available:
            return True
        if self._is_editing_existing and self._current_record is not None:
            return normalized == self._current_record.raw_drum_identification
        return False

    def _save(self) -> None:
        self._validate_form()
        if not self._save_button.isEnabled():
            return

        payload = GomaSecaPayload(
            production_date=self._selected_date,
            lot_code=self._lote_input.text(),
            finision_number=self._selected_finision,
            kg_produced=self._kg_input.value(),
            raw_drum_identification=self._raw_drum_input.text(),
            raw_kg_used=self._raw_kg_input.value(),
            filter_cleanings=self._filter_cleanings_input.value(),
            humidity_percent=self._humidity_input.value(),
            day_start_time=self._day_start_input.time().toString("HH:mm"),
            top_temperature=self._top_temperature_input.value(),
            gum_temperature=self._gum_temperature_input.value(),
            vacuum=self._vacuum_input.value(),
            distillation_minutes=self._distillation_input.value(),
            observations=self._observaciones_input.toPlainText(),
        )
        record_id = self._current_record.id if self._is_editing_existing and self._current_record else None
        production = self._service.save_production(
            payload=payload,
            username=self._username,
            record_id=record_id,
        )
        message = (
            f"Producción guardada para {production.production_date.strftime('%d/%m/%Y')} "
            f"finisión {production.finision_number}: {production.lot_code}."
        )
        self.production_saved.emit(message)
        self._current_record = production
        self._is_editing_existing = False
        self._refresh_form_for_slot()
        self._refresh_week_summary()

    def _refresh_week_summary(self) -> None:
        week_start = self._start_of_week(self._selected_date)
        records = self._service.list_by_week(week_start)
        grouped: dict[date, list[GomaSecaProduction]] = {}
        for item in records:
            grouped.setdefault(item.production_date, []).append(item)

        rows: list[tuple[list[str], bool]] = []
        week_produced = 0.0
        week_consumed = 0.0
        for current_date in sorted(grouped):
            day_items = grouped[current_date]
            day_produced = 0.0
            day_consumed = 0.0
            for item in day_items:
                day_produced += item.kg_produced
                day_consumed += item.raw_kg_used
                week_produced += item.kg_produced
                week_consumed += item.raw_kg_used
                rows.append(
                    (
                        [
                            current_date.strftime("%d/%m/%Y"),
                            item.lot_code,
                            str(item.finision_number),
                            item.raw_drum_identification,
                            f"{item.raw_kg_used:.2f}",
                            f"{item.kg_produced:.2f}",
                            self._format_ratio(item.kg_produced, item.raw_kg_used),
                        ],
                        False,
                    )
                )

            rows.append(
                (
                    [
                        f"Resumen {current_date.strftime('%d/%m/%Y')}",
                        "-",
                        "-",
                        "-",
                        f"{day_consumed:.2f}",
                        f"{day_produced:.2f}",
                        self._format_ratio(day_produced, day_consumed),
                    ],
                    True,
                )
            )

        if rows:
            rows.append(
                (
                    [
                        "Resumen semana",
                        "-",
                        "-",
                        "-",
                        f"{week_consumed:.2f}",
                        f"{week_produced:.2f}",
                        self._format_ratio(week_produced, week_consumed),
                    ],
                    True,
                )
            )

        self._records_table.setRowCount(len(rows))
        for row, (values, summary_row) in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {2, 4, 5, 6}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if summary_row:
                    item.setBackground(QColor("#eef4fa"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self._records_table.setItem(row, column, item)
        self._records_table.resizeColumnsToContents()

    @staticmethod
    def _format_ratio(produced: float, consumed: float) -> str:
        if consumed <= 0:
            return "-"
        return f"{produced / consumed:.3f}"

    @staticmethod
    def _start_of_week(value: date) -> date:
        return value - timedelta(days=value.weekday())

    @staticmethod
    def _time_from_text(value: str) -> QTime:
        parsed = QTime.fromString(value, "HH:mm")
        if parsed.isValid():
            return parsed
        return QTime(7, 0)

    @staticmethod
    def _to_qdate(value: date) -> QDate:
        return QDate(value.year, value.month, value.day)
