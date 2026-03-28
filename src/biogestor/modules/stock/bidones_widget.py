from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.bidon import Bidon
from biogestor.services.bidon_service import BidonService
from biogestor.services.goma_seca_service import GomaSecaService


class BidonVisual(QWidget):
    clicked = Signal()

    _palette = {
        "stock": QColor("#2f80d1"),
        "f0975": QColor("#cf3e36"),
        "f1620": QColor("#8a94a6"),
    }

    def __init__(self, bidon: Bidon) -> None:
        super().__init__()
        self._bidon = bidon
        self.setMinimumSize(180, 220)
        self.setMaximumWidth(220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._build_tooltip())

    def _build_tooltip(self) -> str:
        if self._bidon.status == "stock":
            return f"{self._bidon.identification} en stock"
        process = (self._bidon.consumed_in or "proceso no informado").upper()
        return f"{self._bidon.identification} consumido en {process}"

    def _fill_color(self) -> QColor:
        if self._bidon.status == "stock":
            return self._palette["stock"]
        if (self._bidon.consumed_in or "").lower() == "f0975":
            return self._palette["f0975"]
        return self._palette["f1620"]

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        body_rect = QRectF(28, 32, self.width() - 56, self.height() - 56)
        top_rect = QRectF(body_rect.left() + 10, 16, body_rect.width() - 20, 28)
        shadow_rect = QRectF(body_rect.left() + 12, body_rect.bottom() - 2, body_rect.width() - 24, 12)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 20))
        painter.drawEllipse(shadow_rect)

        fill_color = self._fill_color()
        outline_pen = QPen(QColor("#29445a"))
        outline_pen.setWidth(2)
        painter.setPen(outline_pen)
        painter.setBrush(fill_color)
        painter.drawRoundedRect(body_rect, 22, 22)

        painter.setBrush(fill_color.lighter(112))
        painter.drawEllipse(top_rect)

        stripe_pen = QPen(QColor(255, 255, 255, 55))
        stripe_pen.setWidth(3)
        painter.setPen(stripe_pen)
        for factor in (0.24, 0.42, 0.60, 0.78):
            y = body_rect.top() + (body_rect.height() * factor)
            painter.drawLine(
                QPointF(body_rect.left() + 14, y),
                QPointF(body_rect.right() - 14, y),
            )

        highlight = QPainterPath()
        highlight.addRoundedRect(
            QRectF(body_rect.left() + 12, body_rect.top() + 12, 26, body_rect.height() - 24),
            12,
            12,
        )
        painter.fillPath(highlight, QColor(255, 255, 255, 40))

        label_rect = QRectF(body_rect.left() + 18, body_rect.center().y() - 22, body_rect.width() - 36, 44)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(16, 42, 67, 180))
        painter.drawRoundedRect(label_rect, 8, 8)

        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor("#f8fbff"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._bidon.identification)
        painter.end()
        super().paintEvent(event)


class BidonesWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session], username: str) -> None:
        super().__init__()
        self._username = username
        self._service = BidonService(session_factory)
        self._goma_seca_service = GomaSecaService(session_factory)
        self._completer = QCompleter([])
        self._all_bidones: list[Bidon] = []
        self._last_columns = 0
        self._last_rendered_ids: tuple[str, ...] = ()
        self._build_ui()
        self._refresh_content()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("panelCard")
        header_layout = QVBoxLayout(header)
        title = QLabel("Listado visual de bidones de goma bruta")
        title.setObjectName("sectionTitle")
        summary = QLabel(
            "Busca por identificación y filtra por color para revisar el estado de los bidones."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #486581;")
        header_layout.addWidget(title)
        header_layout.addWidget(summary)

        filters_row = QHBoxLayout()
        filters_row.setSpacing(10)
        self._search_input = QLineEdit()
        self._search_input.setObjectName("bidonSearchInput")
        self._search_input.setPlaceholderText("Buscar bidón por identificación")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.activated.connect(self._apply_completion)
        self._search_input.setCompleter(self._completer)
        filters_row.addWidget(self._search_input, stretch=1)

        self._color_filter = QComboBox()
        self._color_filter.addItem("Todos los colores", "all")
        self._color_filter.addItem("Azules: en stock", "stock")
        self._color_filter.addItem("Grises: goma seca F1620", "f1620")
        self._color_filter.addItem("Rojos: F0975", "f0975")
        self._color_filter.currentIndexChanged.connect(lambda: self._refresh_visuals(force=True))
        filters_row.addWidget(self._color_filter)
        header_layout.addLayout(filters_row)

        self._status_label = QLabel()
        self._status_label.setObjectName("bidonSearchStatus")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #486581;")
        header_layout.addWidget(self._status_label)
        root.addWidget(header)

        visual_panel = QFrame()
        visual_panel.setObjectName("panelCard")
        visual_layout = QVBoxLayout(visual_panel)
        visual_title = QLabel("Bidones de goma bruta")
        visual_title.setObjectName("sectionTitle")
        visual_layout.addWidget(visual_title)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.viewport().installEventFilter(self)
        self._visual_container = QWidget()
        self._visual_grid = QGridLayout(self._visual_container)
        self._visual_grid.setContentsMargins(8, 8, 8, 8)
        self._visual_grid.setHorizontalSpacing(18)
        self._visual_grid.setVerticalSpacing(18)
        self._scroll.setWidget(self._visual_container)
        visual_layout.addWidget(self._scroll)
        root.addWidget(visual_panel, stretch=1)

    def showEvent(self, event) -> None:  # type: ignore[override]
        self._refresh_content()
        super().showEvent(event)

    def eventFilter(self, watched, event) -> bool:  # type: ignore[override]
        if watched is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._refresh_visuals(force=False)
        return super().eventFilter(watched, event)

    def _apply_completion(self, value: str) -> None:
        self._search_input.setText(value)

    def _on_search_changed(self, _value: str) -> None:
        suggestions = self._service.list_identifications(self._search_input.text(), limit=12)
        self._completer.model().setStringList(suggestions)  # type: ignore[union-attr]
        self._refresh_visuals(force=True)

    def _refresh_content(self) -> None:
        self._all_bidones = self._service.list_bidones()
        self._refresh_visuals(force=True)

    def _filtered_bidones(self) -> list[Bidon]:
        query = self._search_input.text().strip().upper()
        color_filter = self._color_filter.currentData()
        items = self._all_bidones

        if color_filter == "stock":
            items = [item for item in items if item.status == "stock"]
        elif color_filter == "f1620":
            items = [item for item in items if (item.consumed_in or "").lower() == "f1620"]
        elif color_filter == "f0975":
            items = [item for item in items if (item.consumed_in or "").lower() == "f0975"]

        if not query:
            return items

        exact_matches = [item for item in items if item.identification == query]
        if exact_matches:
            return exact_matches

        ranked = self._service.list_identifications(query, limit=100)
        rank_map = {identification: index for index, identification in enumerate(ranked)}
        return sorted(
            [item for item in items if query in item.identification],
            key=lambda item: rank_map.get(item.identification, 999),
        )

    def _refresh_visuals(self, *, force: bool) -> None:
        items = self._filtered_bidones()
        columns = self._calculate_columns()
        render_ids = tuple(item.identification for item in items)

        if not force and columns == self._last_columns and render_ids == self._last_rendered_ids:
            self._update_status(items, columns)
            return

        self._last_columns = columns
        self._last_rendered_ids = render_ids

        self._visual_container.setUpdatesEnabled(False)
        try:
            self._clear_grid()
            for index, bidon in enumerate(items):
                row = index // columns
                column = index % columns
                visual = BidonVisual(bidon)
                visual.clicked.connect(lambda item=bidon: self._show_bidon_detail(item))
                self._visual_grid.addWidget(visual, row, column)

            for column in range(columns):
                self._visual_grid.setColumnStretch(column, 1)
            self._visual_grid.setRowStretch((len(items) // max(columns, 1)) + 1, 1)
        finally:
            self._visual_container.setUpdatesEnabled(True)
            self._visual_container.update()

        self._update_status(items, columns)

    def _clear_grid(self) -> None:
        while self._visual_grid.count():
            child = self._visual_grid.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

    def _calculate_columns(self) -> int:
        card_width = 220
        viewport_width = max(self._scroll.viewport().width() - 24, card_width)
        return max(1, viewport_width // card_width)

    def _update_status(self, items: list[Bidon], columns: int) -> None:
        if not self._all_bidones:
            self._status_label.setText("Todavía no hay bidones guardados.")
        elif not items:
            self._status_label.setText("No hay coincidencias para la búsqueda actual.")
        elif len(items) == 1:
            self._status_label.setText(f"Mostrando 1 bidón: {items[0].identification}.")
        else:
            self._status_label.setText(f"Mostrando {len(items)} bidones en {columns} columnas.")

    def _show_bidon_detail(self, bidon: Bidon) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Bidón {bidon.identification}")
        dialog.resize(420, 320)
        layout = QVBoxLayout(dialog)

        title = QLabel(bidon.identification)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.addRow("Lote al que pertenece:", QLabel("Aún no hay lotes"))
        form.addRow("Kg:", QLabel("200 kg"))

        production = self._goma_seca_service.get_by_raw_drum_identification(bidon.identification)
        production_name = "En stock"
        consumed_lot = "-"
        consumed_date = "-"
        if bidon.status != "stock":
            production_name = {
                "f1620": "Goma seca F1620",
                "f0975": "F0975",
            }.get((bidon.consumed_in or "").lower(), "Proceso no informado")
        if production is not None:
            consumed_lot = production.lot_code
            consumed_date = production.production_date.strftime("%d/%m/%Y")

        form.addRow("Producción consumida:", QLabel(production_name))
        form.addRow("Lote consumido:", QLabel(consumed_lot))
        form.addRow("Fecha de consumo:", QLabel(consumed_date))
        layout.addLayout(form)
        dialog.exec()
