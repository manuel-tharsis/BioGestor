from __future__ import annotations

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.services.pending_shipments_service import PendingShipmentItem, PendingShipmentsService


class PendingShipmentsWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._service = PendingShipmentsService(session_factory)
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("pendingShipmentsSummary")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet("color: #486581; font-weight: 600;")
        root.addWidget(self._summary_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(scroll, stretch=1)

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch(1)
        scroll.setWidget(self._cards_container)

    def showEvent(self, event: QShowEvent) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        pending_items = self._service.list_pending_products()
        self._summary_label.setText(
            "Solo se muestran productos terminados pendientes de salida. "
            "La goma bruta no aparece aquí porque siempre queda reservada para consumo interno."
        )
        self._clear_cards()

        if not pending_items:
            self._cards_layout.addWidget(self._build_empty_state())
            self._cards_layout.addStretch(1)
            return

        for item in pending_items:
            self._cards_layout.addWidget(self._build_card(item))
        self._cards_layout.addStretch(1)

    def _build_empty_state(self) -> QWidget:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)

        title = QLabel("No hay envíos pendientes")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        description = QLabel(
            "Cuando una producción terminada quede pendiente de revisar para envío, aparecerá aquí."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #486581;")
        layout.addWidget(description)
        return card

    def _build_card(self, item: PendingShipmentItem) -> QWidget:
        card = QFrame()
        card.setObjectName("panelCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel(item.label)
        title.setObjectName("sectionTitle")
        title.setStyleSheet("color: #17324d; font-size: 18px; font-weight: 800;")
        layout.addWidget(title)

        description = QLabel(item.description)
        description.setWordWrap(True)
        description.setStyleSheet("color: #486581;")
        layout.addWidget(description)

        metrics = QHBoxLayout()
        metrics.setSpacing(18)
        metrics.addWidget(self._build_metric("Lotes pendientes", str(item.lot_count)))
        metrics.addWidget(self._build_metric("Kg pendientes", f"{item.kg_total:.0f} kg"))
        metrics.addWidget(
            self._build_metric("Última producción", item.latest_production_date.strftime("%d/%m/%Y"))
        )
        metrics.addStretch(1)
        layout.addLayout(metrics)

        lots = QLabel(f"Lotes: {', '.join(item.lots)}")
        lots.setWordWrap(True)
        lots.setStyleSheet("color: #334e68;")
        layout.addWidget(lots)
        return card

    def _build_metric(self, label: str, value: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #7b8794; font-size: 12px; font-weight: 700;")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet("color: #17324d; font-size: 16px; font-weight: 800;")
        layout.addWidget(value_widget)
        return widget

    def _clear_cards(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
