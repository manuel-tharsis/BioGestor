from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from biogestor.auth.roles import Role
from biogestor.db.models.user import User
from biogestor.services.auth_service import AuthService


class InitialSetupDialog(QDialog):
    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self._auth_service = auth_service
        self._created_user: User | None = None

        self.setWindowTitle("Configuracion inicial - BioGestor")
        self.setModal(True)
        self.resize(460, 220)
        self._build_ui()

    @property
    def created_user(self) -> User | None:
        return self._created_user

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Primer arranque")
        title.setObjectName("setupTitle")
        layout.addWidget(title)

        helper = QLabel(
            "No existen usuarios en la base de datos. Crea ahora el administrador "
            "inicial para entrar en la aplicacion."
        )
        helper.setWordWrap(True)
        layout.addWidget(helper)

        form = QFormLayout()
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("admin")
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Minimo 8 caracteres")
        self._confirm_password_input = QLineEdit()
        self._confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._confirm_password_input.setPlaceholderText("Repite la password")

        form.addRow("Usuario admin:", self._username_input)
        form.addRow("Password:", self._password_input)
        form.addRow("Confirmar:", self._confirm_password_input)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        create_button = QPushButton("Crear y entrar")
        create_button.clicked.connect(self._submit)
        create_button.setDefault(True)
        actions.addWidget(create_button)
        layout.addLayout(actions)

        self._username_input.setText("admin")
        self._username_input.selectAll()
        self._username_input.setFocus()

    def _submit(self) -> None:
        username = self._username_input.text().strip()
        password = self._password_input.text()
        confirm_password = self._confirm_password_input.text()

        if not username:
            QMessageBox.warning(self, "Configuracion inicial", "Introduce un usuario.")
            self._username_input.setFocus()
            return

        if password != confirm_password:
            QMessageBox.warning(
                self,
                "Configuracion inicial",
                "Las passwords no coinciden.",
            )
            self._confirm_password_input.clear()
            self._confirm_password_input.setFocus()
            return

        try:
            self._created_user = self._auth_service.create_user(
                username=username,
                password=password,
                role=Role.ADMIN,
                created_by="system",
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Configuracion inicial", str(exc))
            self._password_input.clear()
            self._confirm_password_input.clear()
            self._password_input.setFocus()
            return

        QMessageBox.information(
            self,
            "Configuracion inicial",
            "Administrador creado correctamente. Se abrira la aplicacion.",
        )
        self.accept()
