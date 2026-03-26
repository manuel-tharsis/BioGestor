from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from biogestor.auth.roles import Role
from biogestor.db.base import Base
from biogestor.db import models  # noqa: F401
from biogestor.services.auth_service import AuthService


def _session_factory() -> sessionmaker:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_auth_service_create_user_and_authenticate() -> None:
    auth_service = AuthService(_session_factory())

    assert not auth_service.has_users()

    created_user = auth_service.create_user(
        username="admin",
        password="super-segura",
        role=Role.ADMIN,
    )

    assert created_user.username == "admin"
    assert auth_service.has_users()

    result = auth_service.authenticate("admin", "super-segura")

    assert result.success
    assert result.user is not None
    assert result.user.username == "admin"
