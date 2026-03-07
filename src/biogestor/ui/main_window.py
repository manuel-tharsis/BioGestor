from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

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

        menu = QTreeWidget()
        menu.setHeaderLabel("Menu")
        for node in MENU_TREE:
            menu.addTopLevelItem(self._build_tree_item(node))
        menu.expandAll()

        placeholder = QLabel("Selecciona un modulo para comenzar.")
        placeholder.setMargin(12)

        splitter.addWidget(menu)
        splitter.addWidget(placeholder)
        splitter.setStretchFactor(1, 1)
        return splitter

    def _build_tree_item(self, node: MenuNode) -> QTreeWidgetItem:
        item = QTreeWidgetItem([node.label])
        item.setData(0, 0x0100, node.key)
        for child in node.children:
            item.addChild(self._build_tree_item(child))
        return item
