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

from biogestor.db.models.user import User
from biogestor.services.auth_service import AuthService


class LoginDialog(QDialog):
    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self._auth_service = auth_service
        self._authenticated_user: User | None = None

        self.setWindowTitle("Acceso - BioGestor")
        self.setModal(True)
        self.resize(420, 180)
        self._build_ui()

    @property
    def authenticated_user(self) -> User | None:
        return self._authenticated_user

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Introduce tus credenciales"))

        form = QFormLayout()
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("Usuario")
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText("Password")

        form.addRow("Usuario", self._username_input)
        form.addRow("Password", self._password_input)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        submit = QPushButton("Entrar")
        submit.clicked.connect(self._submit)
        submit.setDefault(True)
        actions.addWidget(cancel)
        actions.addWidget(submit)
        layout.addLayout(actions)

    def _submit(self) -> None:
        result = self._auth_service.authenticate(
            self._username_input.text(),
            self._password_input.text(),
        )
        if not result.success or result.user is None:
            QMessageBox.warning(self, "Login", result.reason or "Credenciales invalidas.")
            self._password_input.clear()
            self._password_input.setFocus()
            return
        self._authenticated_user = result.user
        self.accept()

