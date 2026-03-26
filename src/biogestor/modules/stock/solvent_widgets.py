from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.services.solvent_week_metric_service import (
    SolventWeekMetricService,
    SolventWeekSnapshot,
)


@dataclass(frozen=True)
class MetricVisualSpec:
    title: str
    liters: float
    limit: float
    color: str
    kind: str


class SolventMetricVisual(QWidget):
    def __init__(self, spec: MetricVisualSpec) -> None:
        super().__init__()
        self._spec = spec
        self.setMinimumSize(260, 280)

    def update_spec(self, spec: MetricVisualSpec) -> None:
        self._spec = spec
        self.update()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#ffffff"))

        title_font = QFont(self.font())
        title_font.setBold(True)
        title_font.setPointSize(12)
        painter.setFont(title_font)
        painter.setPen(QColor("#17324d"))
        painter.drawText(QRectF(18, 16, self.width() - 36, 24), self._spec.title)

        ratio = 0.0 if self._spec.limit <= 0 else max(0.0, min(1.0, self._spec.liters / self._spec.limit))
        liquid = QColor(self._spec.color)

        if self._spec.kind == "truck":
            self._draw_truck(painter, liquid, ratio)
        elif self._spec.kind == "tank":
            self._draw_tank(painter, liquid, ratio)
        else:
            self._draw_consumption(painter, liquid, ratio)

        text_font = QFont(self.font())
        text_font.setBold(True)
        text_font.setPointSize(11)
        painter.setFont(text_font)
        painter.setPen(QColor("#102a43"))
        painter.drawText(
            QRectF(18, self.height() - 52, self.width() - 36, 20),
            Qt.AlignmentFlag.AlignCenter,
            f"{self._spec.liters:.0f} L / {self._spec.limit:.0f} L",
        )
        painter.setPen(QColor("#486581"))
        painter.drawText(
            QRectF(18, self.height() - 28, self.width() - 36, 18),
            Qt.AlignmentFlag.AlignCenter,
            f"{ratio * 100:.0f}% de capacidad visual",
        )
        painter.end()
        super().paintEvent(event)

    def _draw_truck(self, painter: QPainter, liquid: QColor, ratio: float) -> None:
        body = QRectF(40, 96, 138, 78)
        cabin = QRectF(178, 112, 44, 62)
        cargo = QRectF(body.left() + 6, body.top() + 10, body.width() - 12, body.height() - 18)
        fill_height = cargo.height() * ratio

        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(QColor("#eef4fa"))
        painter.drawRoundedRect(body, 14, 14)
        painter.drawRoundedRect(cabin, 10, 10)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(liquid)
        painter.drawRect(
            QRectF(cargo.left(), cargo.bottom() - fill_height, cargo.width(), fill_height)
        )
        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(cargo, 10, 10)
        painter.setBrush(QColor("#29445a"))
        painter.drawEllipse(QRectF(62, 172, 28, 28))
        painter.drawEllipse(QRectF(170, 172, 28, 28))

    def _draw_tank(self, painter: QPainter, liquid: QColor, ratio: float) -> None:
        tank = QRectF(72, 74, 116, 136)
        inner = QRectF(tank.left() + 10, tank.top() + 14, tank.width() - 20, tank.height() - 24)
        fill_height = inner.height() * ratio

        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(QColor("#eef4fa"))
        painter.drawRoundedRect(tank, 24, 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(liquid)
        painter.drawRoundedRect(
            QRectF(inner.left(), inner.bottom() - fill_height, inner.width(), fill_height),
            16,
            16,
        )
        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner, 16, 16)

    def _draw_consumption(self, painter: QPainter, liquid: QColor, ratio: float) -> None:
        tank = QRectF(40, 74, 84, 120)
        trash = QRectF(158, 116, 60, 84)
        inner_tank = QRectF(tank.left() + 8, tank.top() + 10, tank.width() - 16, tank.height() - 18)
        inner_trash = QRectF(trash.left() + 8, trash.top() + 10, trash.width() - 16, trash.height() - 18)
        fill_height = inner_trash.height() * ratio

        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(QColor("#eef4fa"))
        painter.drawRoundedRect(tank, 18, 18)
        painter.drawRoundedRect(trash, 10, 10)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#8db7e0"))
        painter.drawRoundedRect(inner_tank, 12, 12)
        painter.setBrush(liquid)
        painter.drawRoundedRect(
            QRectF(inner_trash.left(), inner_trash.bottom() - fill_height, inner_trash.width(), fill_height),
            8,
            8,
        )

        pipe = QPainterPath()
        pipe.moveTo(tank.right(), tank.center().y() - 12)
        pipe.lineTo(148, tank.center().y() - 12)
        pipe.lineTo(148, 108)
        pipe.lineTo(trash.center().x(), 108)
        painter.setPen(QPen(QColor("#29445a"), 8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(pipe)

        painter.setPen(QPen(liquid, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(
            QPointF(trash.center().x(), 108),
            QPointF(trash.center().x(), 126),
        )
        painter.setPen(QPen(QColor("#29445a"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(inner_trash, 8, 8)


class HexanoWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._service = SolventWeekMetricService(session_factory)
        self._week_start = self._start_of_week(date.today())
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        week_row = QHBoxLayout()
        prev_button = QPushButton("<")
        prev_button.clicked.connect(self._go_previous_week)
        next_button = QPushButton(">")
        next_button.clicked.connect(self._go_next_week)
        self._week_label = QLabel()
        self._week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._week_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #17324d;")
        week_row.addWidget(prev_button)
        week_row.addWidget(self._week_label, stretch=1)
        week_row.addWidget(next_button)
        root.addLayout(week_row)

        visuals_row = QHBoxLayout()
        visuals_row.setSpacing(16)
        self._purchase_visual = SolventMetricVisual(
            MetricVisualSpec("Compras", 0.0, 20000.0, "#3f9b53", "truck")
        )
        self._stock_visual = SolventMetricVisual(
            MetricVisualSpec("Stock", 0.0, 20000.0, "#2f80d1", "tank")
        )
        self._consumption_visual = SolventMetricVisual(
            MetricVisualSpec("Consumido", 0.0, 5000.0, "#cf3e36", "consumption")
        )
        visuals_row.addWidget(self._purchase_visual)
        visuals_row.addWidget(self._stock_visual)
        visuals_row.addWidget(self._consumption_visual)
        root.addLayout(visuals_row)

        info_card = QFrame()
        info_card.setObjectName("panelCard")
        info_layout = QVBoxLayout(info_card)
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #486581;")
        info_layout.addWidget(self._status_label)
        root.addWidget(info_card)

    def _go_previous_week(self) -> None:
        self._week_start -= timedelta(days=7)
        self._refresh()

    def _go_next_week(self) -> None:
        self._week_start += timedelta(days=7)
        self._refresh()

    def _refresh(self) -> None:
        snapshot = self._service.get_snapshot(solvent_name="hexano", week_start=self._week_start)
        week_end = self._week_start + timedelta(days=6)
        iso_week = self._week_start.isocalendar().week
        self._week_label.setText(
            f"Semana {iso_week} ({self._week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})"
        )
        self._purchase_visual.update_spec(
            MetricVisualSpec("Compras", snapshot.purchases_liters, 20000.0, "#3f9b53", "truck")
        )
        self._stock_visual.update_spec(
            MetricVisualSpec("Stock", snapshot.stock_liters, 20000.0, "#2f80d1", "tank")
        )
        self._consumption_visual.update_spec(
            MetricVisualSpec("Consumido", snapshot.consumed_liters, 5000.0, "#cf3e36", "consumption")
        )
        if snapshot.has_data:
            self._status_label.setText("Mostrando datos guardados para esta semana.")
        else:
            self._status_label.setText(
                "No hay datos cargados para esta semana. La visualizacion se muestra vacia."
            )

    @staticmethod
    def _start_of_week(value: date) -> date:
        return value - timedelta(days=value.weekday())


class IsopropanolWidget(QWidget):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        super().__init__()
        self._service = SolventWeekMetricService(session_factory)
        self._week_start = self._start_of_week(date.today())
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        week_row = QHBoxLayout()
        prev_button = QPushButton("<")
        prev_button.clicked.connect(self._go_previous_week)
        next_button = QPushButton(">")
        next_button.clicked.connect(self._go_next_week)
        self._week_label = QLabel()
        self._week_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._week_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #17324d;")
        week_row.addWidget(prev_button)
        week_row.addWidget(self._week_label, stretch=1)
        week_row.addWidget(next_button)
        root.addLayout(week_row)

        card = QFrame()
        card.setObjectName("panelCard")
        card_layout = QVBoxLayout(card)
        title = QLabel("Isopropanol")
        title.setObjectName("sectionTitle")
        self._status_label = QLabel()
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet("color: #486581;")
        card_layout.addWidget(title)
        card_layout.addWidget(self._status_label)
        root.addWidget(card)

    def _go_previous_week(self) -> None:
        self._week_start -= timedelta(days=7)
        self._refresh()

    def _go_next_week(self) -> None:
        self._week_start += timedelta(days=7)
        self._refresh()

    def _refresh(self) -> None:
        snapshot = self._service.get_snapshot(
            solvent_name="isopropanol",
            week_start=self._week_start,
        )
        week_end = self._week_start + timedelta(days=6)
        iso_week = self._week_start.isocalendar().week
        self._week_label.setText(
            f"Semana {iso_week} ({self._week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')})"
        )
        if snapshot.has_data:
            self._status_label.setText(
                f"Compras: {snapshot.purchases_liters:.0f} L | "
                f"Stock: {snapshot.stock_liters:.0f} L | "
                f"Consumido: {snapshot.consumed_liters:.0f} L"
            )
        else:
            self._status_label.setText(
                "No hay datos cargados para esta semana. La pantalla queda preparada para consulta."
            )

    @staticmethod
    def _start_of_week(value: date) -> date:
        return value - timedelta(days=value.weekday())
