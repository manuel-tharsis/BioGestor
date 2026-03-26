from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.models.bidon import Bidon
from biogestor.services.bidon_service import BidonService


class BidonVisual(QWidget):
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
        self.setToolTip(self._build_tooltip())

    def _build_tooltip(self) -> str:
        if self._bidon.status == "stock":
            return f"{self._bidon.identification} en stock"
        return (
            f"{self._bidon.identification} consumido en "
            f"{self._bidon.consumed_in or 'proceso no informado'}"
        )

    def _fill_color(self) -> QColor:
        if self._bidon.status == "stock":
            return self._palette["stock"]
        if (self._bidon.consumed_in or "").lower() == "f0975":
            return self._palette["f0975"]
        return self._palette["f1620"]

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fbff"))

        body_rect = QRectF(28, 32, self.width() - 56, self.height() - 56)
        top_rect = QRectF(body_rect.left() + 10, 16, body_rect.width() - 20, 28)
        shadow_rect = QRectF(
            body_rect.left() + 12, body_rect.bottom() - 2, body_rect.width() - 24, 12
        )

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
            QRectF(
                body_rect.left() + 12,
                body_rect.top() + 12,
                26,
                body_rect.height() - 24,
            ),
            12,
            12,
        )
        painter.fillPath(highlight, QColor(255, 255, 255, 40))

        label_rect = QRectF(
            body_rect.left() + 18,
            body_rect.center().y() - 22,
            body_rect.width() - 36,
            44,
        )
        painter.setPen(QPen(QColor("#d6dbe2"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(label_rect, 8, 8)

        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QColor("#111111"))
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, self._bidon.identification)

        painter.end()
        super().paintEvent(event)


class BidonesWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session], username: str) -> None:
        super().__init__()
        self._username = username
        self._service = BidonService(session_factory)
        self._completer = QCompleter([])
        self._all_bidones: list[Bidon] = []
        self._build_ui()
        self._refresh_content()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("panelCard")
        header_layout = QVBoxLayout(header)
        title = QLabel("Listado visual de bidones")
        title.setObjectName("sectionTitle")
        summary = QLabel(
            "Escribe una identificacion para localizar un bidon exacto o usa las "
            "sugerencias para encontrar coincidencias."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: #486581;")
        header_layout.addWidget(title)
        header_layout.addWidget(summary)

        self._search_input = QLineEdit()
        self._search_input.setObjectName("bidonSearchInput")
        self._search_input.setPlaceholderText("Buscar bidon por identificacion")
        self._search_input.textChanged.connect(self._on_search_changed)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.activated.connect(self._apply_completion)
        self._search_input.setCompleter(self._completer)
        header_layout.addWidget(self._search_input)

        self._status_label = QLabel()
        self._status_label.setObjectName("bidonSearchStatus")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #486581;")
        header_layout.addWidget(self._status_label)
        root.addWidget(header)

        visual_panel = QFrame()
        visual_panel.setObjectName("panelCard")
        visual_layout = QVBoxLayout(visual_panel)
        visual_title = QLabel("Bidones")
        visual_title.setObjectName("sectionTitle")
        visual_layout.addWidget(visual_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._visual_container = QWidget()
        self._visual_grid = QGridLayout(self._visual_container)
        self._visual_grid.setContentsMargins(8, 8, 8, 8)
        self._visual_grid.setHorizontalSpacing(18)
        self._visual_grid.setVerticalSpacing(18)
        scroll.setWidget(self._visual_container)
        visual_layout.addWidget(scroll)
        root.addWidget(visual_panel, stretch=1)

    def _apply_completion(self, value: str) -> None:
        self._search_input.setText(value)

    def _on_search_changed(self, _value: str) -> None:
        suggestions = self._service.list_identifications(self._search_input.text())
        self._completer.model().setStringList(suggestions)  # type: ignore[union-attr]
        self._refresh_visuals()

    def _refresh_content(self) -> None:
        self._all_bidones = self._service.list_bidones()
        self._on_search_changed(self._search_input.text())

    def _filtered_bidones(self) -> list[Bidon]:
        query = self._search_input.text().strip().upper()
        if not query:
            return self._all_bidones

        exact_matches = [item for item in self._all_bidones if item.identification == query]
        if exact_matches:
            return exact_matches

        return [item for item in self._all_bidones if query in item.identification]

    def _refresh_visuals(self) -> None:
        items = self._filtered_bidones()
        while self._visual_grid.count():
            child = self._visual_grid.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()

        for index, bidon in enumerate(items):
            row = index // 4
            column = index % 4
            self._visual_grid.addWidget(BidonVisual(bidon), row, column)

        self._visual_grid.setColumnStretch(4, 1)
        self._visual_grid.setRowStretch((len(items) // 4) + 1, 1)

        if not self._all_bidones:
            self._status_label.setText("Todavia no hay bidones guardados.")
        elif not items:
            self._status_label.setText("No hay coincidencias para la busqueda actual.")
        elif len(items) == 1:
            self._status_label.setText(f"Mostrando 1 bidon: {items[0].identification}.")
        else:
            self._status_label.setText(f"Mostrando {len(items)} bidones.")
