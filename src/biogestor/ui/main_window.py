from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session, sessionmaker

from biogestor.modules.consultas import ConsultasWidget
from biogestor.modules.module_registry import MENU_TREE, MenuNode
from biogestor.modules.producciones.goma_seca_widget import GomaSecaWidget
from biogestor.modules.stock import BidonesWidget, HexanoWidget, IsopropanolWidget


@dataclass
class NavigationEntry:
    key: str
    label: str
    widget: QWidget
    back_button: QPushButton | None = None


class MainWindow(QMainWindow):
    def __init__(
        self,
        username: str,
        role: str,
        session_factory: sessionmaker[Session],
    ) -> None:
        super().__init__()
        self._username = username
        self._role = role
        self._session_factory = session_factory
        self._entries_by_key: dict[str, NavigationEntry] = {}
        self._navigation_history: list[str] = []
        self._current_key = "inicio"
        self.setWindowTitle("BioGestor")
        self.resize(1200, 760)
        self.setCentralWidget(self._build_layout())
        self._apply_styles()
        self.statusBar().showMessage(f"Usuario: {username} | Rol: {role}")

    def _build_layout(self) -> QWidget:
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 14, 16, 14)

        self._menu_button = QPushButton("MENÚ")
        self._menu_button.setObjectName("menuButton")
        self._menu_button.clicked.connect(self._toggle_menu_panel)
        top_layout.addWidget(self._menu_button, alignment=Qt.AlignmentFlag.AlignLeft)

        title = QLabel("BioGestor")
        title.setObjectName("topBarTitle")
        top_layout.addWidget(title)
        top_layout.addStretch(1)

        user_label = QLabel(f"{self._username} | {self._role}")
        user_label.setObjectName("topBarUser")
        top_layout.addWidget(user_label, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(top_bar)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self._menu_panel = self._build_menu_panel()
        body_layout.addWidget(self._menu_panel)

        self._content = QStackedWidget()
        body_layout.addWidget(self._content, stretch=1)
        root.addWidget(body, stretch=1)

        self._register_initial_pages()
        self._register_navigation_pages()
        self._show_home()
        return container

    def _build_menu_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("menuPanel")
        panel.setFixedWidth(300)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Navegación")
        title.setObjectName("menuTitle")
        layout.addWidget(title)

        home_button = QPushButton("INICIO")
        home_button.setObjectName("homeButton")
        home_button.clicked.connect(self._show_home)
        layout.addWidget(home_button)

        self._menu = QTreeWidget()
        self._menu.setHeaderHidden(True)
        for node in MENU_TREE:
            self._menu.addTopLevelItem(self._build_tree_item(node))
        self._menu.expandAll()
        self._menu.itemClicked.connect(self._on_menu_item_clicked)
        layout.addWidget(self._menu, stretch=1)
        panel.hide()
        return panel

    def _register_initial_pages(self) -> None:
        self._register_entry("inicio", "Inicio", self._build_dashboard())
        goma = GomaSecaWidget(self._session_factory, self._username)
        goma.production_saved.connect(self.statusBar().showMessage)
        self._register_entry(
            "producciones.goma_seca",
            "Goma seca F1620",
            self._wrap_content_page(
                "Goma seca F1620",
                "Registro diario por finisión y resumen semanal de goma seca F1620.",
                goma,
            ),
        )
        self._register_entry(
            "consultas.goma_seca_f1620",
            "Goma seca F1620",
            self._wrap_content_page(
                "Goma seca F1620",
                "Consulta los registros guardados de goma seca F1620.",
                ConsultasWidget(self._session_factory),
            ),
        )
        self._register_entry(
            "stock.bidones",
            "Bidones de Goma Bruta",
            self._wrap_content_page(
                "Bidones de Goma Bruta",
                "Consulta visual del stock y consumo de bidones de goma bruta.",
                BidonesWidget(self._session_factory, self._username),
            ),
        )
        self._register_entry(
            "stock.disolventes.hexano",
            "Hexano",
            self._wrap_content_page(
                "Hexano",
                "Consulta visual semanal de compras, stock y consumido.",
                HexanoWidget(self._session_factory),
            ),
        )
        self._register_entry(
            "stock.disolventes.isopropanol",
            "Isopropanol",
            self._wrap_content_page(
                "Isopropanol",
                "Consulta semanal preparada para este disolvente.",
                IsopropanolWidget(self._session_factory),
            ),
        )

    def _register_navigation_pages(self) -> None:
        for node in MENU_TREE:
            self._register_node_page(node)

    def _register_node_page(self, node: MenuNode) -> None:
        if node.key not in self._entries_by_key:
            widget = (
                self._build_section_page(node)
                if node.children
                else self._build_pending_page(node.label)
            )
            self._register_entry(node.key, node.label.title(), widget)

        for child in node.children:
            self._register_node_page(child)

    def _register_entry(self, key: str, label: str, widget: QWidget) -> None:
        back_button = widget.findChild(QPushButton, "historyBackButton")
        self._entries_by_key[key] = NavigationEntry(
            key=key,
            label=label,
            widget=widget,
            back_button=back_button,
        )
        self._content.addWidget(widget)

    def _show_home(self) -> None:
        self._menu.clearSelection()
        self._open_view("inicio", push_history=False)

    def _toggle_menu_panel(self) -> None:
        self._menu_panel.setVisible(not self._menu_panel.isVisible())

    def _on_menu_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        key = item.data(0, 0x0100)
        self._open_view(key)

    def _build_tree_item(self, node: MenuNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem([node.label])
        item.setData(0, 0x0100, node.key)
        for child in node.children:
            item.addChild(self._build_tree_item(child))
        return item

    def _build_dashboard(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header_card = QFrame()
        header_card.setObjectName("heroCard")
        header_layout = QVBoxLayout(header_card)
        title = QLabel("Panel principal")
        title.setObjectName("heroTitle")
        summary = QLabel(
            f"Sesión iniciada como {self._username} ({self._role}). "
            "Selecciona un módulo principal para seguir navegando."
        )
        summary.setWordWrap(True)
        summary.setObjectName("heroSummary")
        header_layout.addWidget(title)
        header_layout.addWidget(summary)
        layout.addWidget(header_card)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        cards_container = QWidget()
        cards_layout = QGridLayout(cards_container)
        cards_layout.setContentsMargins(4, 4, 4, 4)
        cards_layout.setHorizontalSpacing(18)
        cards_layout.setVerticalSpacing(18)

        for index, node in enumerate(MENU_TREE):
            cards_layout.addWidget(
                self._build_menu_card(node.label, node.key, dark=True),
                index // 3,
                index % 3,
            )

        for index in range(3):
            cards_layout.setColumnStretch(index, 1)
        scroll.setWidget(cards_container)
        layout.addWidget(scroll, stretch=1)
        return container

    def _build_menu_card(self, label: str, key: str, *, dark: bool) -> QWidget:
        button = QPushButton(label)
        button.setObjectName("homeMenuCard" if dark else "sectionMenuCard")
        button.setMinimumHeight(118)
        button.clicked.connect(lambda: self._open_view(key))
        return button

    def _build_shell(self, title: str, summary: str, body: QWidget) -> tuple[QWidget, QPushButton]:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        header = QFrame()
        header.setObjectName("heroCard")
        header_layout = QVBoxLayout(header)
        title_label = QLabel(title)
        title_label.setObjectName("heroTitle")
        summary_label = QLabel(summary)
        summary_label.setObjectName("heroSummary")
        summary_label.setWordWrap(True)
        header_layout.addWidget(title_label)
        header_layout.addWidget(summary_label)
        layout.addWidget(header)

        back_button = QPushButton("Volver a Inicio")
        back_button.setObjectName("historyBackButton")
        back_button.clicked.connect(self._go_back)
        layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(body, stretch=1)
        return container, back_button

    def _wrap_content_page(self, title: str, summary: str, content: QWidget) -> QWidget:
        page, _button = self._build_shell(title, summary, content)
        return page

    def _build_section_page(self, node: MenuNode) -> QWidget:
        grid_container = QWidget()
        grid = QGridLayout(grid_container)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(18)
        for index, child in enumerate(node.children):
            grid.addWidget(
                self._build_menu_card(child.label, child.key, dark=False),
                index // 3,
                index % 3,
            )
        for index in range(3):
            grid.setColumnStretch(index, 1)
        page, _button = self._build_shell(
            node.label,
            "Selecciona uno de los apartados disponibles.",
            grid_container,
        )
        return page

    def _build_pending_page(self, label: str) -> QWidget:
        body = QFrame()
        body.setObjectName("panelCard")
        body_layout = QVBoxLayout(body)
        message = QLabel("Esta pantalla aún no está operativa.")
        message.setWordWrap(True)
        message.setStyleSheet("color: #486581;")
        body_layout.addWidget(message)
        page, _button = self._build_shell(label, "Pantalla pendiente de desarrollo.", body)
        return page

    def _go_back(self) -> None:
        if not self._navigation_history:
            self._open_view("inicio", push_history=False)
            return
        previous_key = self._navigation_history.pop()
        self._open_view(previous_key, push_history=False)

    def _open_view(self, key: str, *, push_history: bool = True) -> None:
        if key not in self._entries_by_key:
            key = "inicio"
        if push_history and self._current_key != key:
            self._navigation_history.append(self._current_key)
        self._current_key = key
        entry = self._entries_by_key[key]
        self._content.setCurrentWidget(entry.widget)
        self._sync_back_buttons()
        if key != "inicio":
            self._menu_panel.hide()

    def _sync_back_buttons(self) -> None:
        previous_label = "Inicio"
        if self._navigation_history:
            previous_key = self._navigation_history[-1]
            previous_label = self._entries_by_key.get(previous_key, self._entries_by_key["inicio"]).label
        for key, entry in self._entries_by_key.items():
            if entry.back_button is None:
                continue
            entry.back_button.setText(f"Volver a {previous_label}")
            entry.back_button.setVisible(key != "inicio")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f4f7fb;
            }
            QFrame#topBar {
                background: #17324d;
                border-bottom: 1px solid #29445a;
            }
            QPushButton#menuButton, QPushButton#homeButton, QPushButton#historyBackButton {
                background: #f3f7fb;
                color: #17324d;
                border: 1px solid #c7d2de;
                border-radius: 12px;
                padding: 11px 18px;
                font-weight: 700;
            }
            QLabel#topBarTitle {
                color: #ffffff;
                font-size: 20px;
                font-weight: 700;
                padding-left: 12px;
            }
            QLabel#topBarUser {
                color: #d9e7f2;
                font-weight: 600;
            }
            QFrame#menuPanel {
                background: #17324d;
                border-right: 1px solid #29445a;
            }
            QLabel#menuTitle {
                color: #f4f7fb;
                font-size: 18px;
                font-weight: 700;
                padding: 4px 6px;
            }
            QTreeWidget {
                background: transparent;
                color: #f4f7fb;
                border: none;
                padding: 4px;
                font-weight: 600;
            }
            QTreeWidget::item {
                padding: 8px 6px;
                border-radius: 6px;
            }
            QTreeWidget::item:selected {
                background: #2b5d87;
            }
            QFrame#heroCard, QFrame#panelCard {
                background: white;
                border: 1px solid #d9e2ec;
                border-radius: 16px;
            }
            QPushButton#homeMenuCard {
                background: #17324d;
                border: 1px solid #29445a;
                border-radius: 20px;
                padding: 22px;
                text-align: left;
                color: #f4f7fb;
                font-size: 19px;
                font-weight: 800;
            }
            QPushButton#homeMenuCard:hover {
                background: #23476b;
            }
            QPushButton#sectionMenuCard {
                background: white;
                border: 1px solid #d9e2ec;
                border-radius: 20px;
                padding: 22px;
                text-align: left;
                color: #17324d;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#sectionMenuCard:hover {
                background: #eef4fa;
                border-color: #9fb9d2;
            }
            QLabel#heroTitle {
                font-size: 24px;
                font-weight: 700;
                color: #102a43;
            }
            QLabel#heroSummary {
                color: #486581;
                font-size: 14px;
            }
            QLabel#sectionTitle {
                color: #334e68;
                font-weight: 700;
            }
            """
        )
