from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStackedWidget,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from biogestor.modules.producciones.goma_seca_widget import GomaSecaWidget
from biogestor.modules.module_registry import MENU_TREE, MenuNode


class MainWindow(QMainWindow):
    def __init__(self, username: str, role: str) -> None:
        super().__init__()
        self.setWindowTitle("BioGestor")
        self.resize(1200, 760)
        self.setCentralWidget(self._build_layout())
        self.statusBar().showMessage(f"Usuario: {username} | Rol: {role}")

    def _build_layout(self) -> QWidget:
        splitter = QSplitter()

        self._menu = QTreeWidget()
        self._menu.setHeaderLabel("Menu")
        for node in MENU_TREE:
            self._menu.addTopLevelItem(self._build_tree_item(node))
        self._menu.expandAll()
        self._menu.itemSelectionChanged.connect(self._on_menu_selection_changed)

        self._content = QStackedWidget()
        self._placeholder = QLabel("Selecciona un modulo para comenzar.")
        self._placeholder.setMargin(12)
        self._goma_seca_widget = GomaSecaWidget()

        self._view_by_key: dict[str, QWidget] = {
            "producciones.goma_seca": self._goma_seca_widget,
        }
        self._content.addWidget(self._placeholder)
        self._content.addWidget(self._goma_seca_widget)

        splitter.addWidget(self._menu)
        splitter.addWidget(self._content)
        splitter.setStretchFactor(1, 1)
        return splitter

    def _on_menu_selection_changed(self) -> None:
        current = self._menu.currentItem()
        if current is None:
            self._content.setCurrentWidget(self._placeholder)
            return

        key = current.data(0, 0x0100)
        widget = self._view_by_key.get(key, self._placeholder)
        self._content.setCurrentWidget(widget)

    def _build_tree_item(self, node: MenuNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem([node.label])
        item.setData(0, 0x0100, node.key)
        for child in node.children:
            item.addChild(self._build_tree_item(child))
        return item
