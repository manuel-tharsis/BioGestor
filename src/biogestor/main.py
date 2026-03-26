import logging

from PySide6.QtWidgets import QApplication, QMessageBox
from sqlalchemy.exc import SQLAlchemyError

from biogestor.config.settings import get_settings
from biogestor.core.logging_config import configure_logging
from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.db.session import SessionLocal, engine
from biogestor.services.auth_service import AuthService
from biogestor.ui.initial_setup_dialog import InitialSetupDialog
from biogestor.ui.login_dialog import LoginDialog
from biogestor.ui.main_window import MainWindow


def run() -> int:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = QApplication([])
    app.setApplicationName(settings.app_name)

    logging.getLogger(__name__).info("Iniciando %s", settings.app_name)

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as exc:
        QMessageBox.critical(
            None,
            "BioGestor",
            "No se pudo preparar la base de datos.\n\n"
            f"Configuracion actual: {settings.database_url}\n\n"
            f"Detalle: {exc}",
        )
        return 1

    auth_service = AuthService(SessionLocal)
    authenticated_user = None

    if not auth_service.has_users():
        initial_setup = InitialSetupDialog(auth_service)
        if initial_setup.exec() == 0 or initial_setup.created_user is None:
            return 0
        authenticated_user = initial_setup.created_user
    else:
        login = LoginDialog(auth_service)
        if login.exec() == 0 or login.authenticated_user is None:
            return 0
        authenticated_user = login.authenticated_user

    window = MainWindow(
        authenticated_user.username,
        authenticated_user.role,
        SessionLocal,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
