import logging

from PySide6.QtWidgets import QApplication

from biogestor.config.settings import get_settings
from biogestor.core.logging_config import configure_logging
from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.db.session import SessionLocal, engine
from biogestor.services.auth_service import AuthService
from biogestor.ui.login_dialog import LoginDialog
from biogestor.ui.main_window import MainWindow


def run() -> int:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = QApplication([])
    app.setApplicationName(settings.app_name)

    logging.getLogger(__name__).info("Iniciando %s", settings.app_name)

    Base.metadata.create_all(bind=engine)

    auth_service = AuthService(SessionLocal)
    login = LoginDialog(auth_service)
    if login.exec() == 0 or login.authenticated_user is None:
        return 0

    window = MainWindow(login.authenticated_user.username, login.authenticated_user.role)
    window.show()
    return app.exec()
