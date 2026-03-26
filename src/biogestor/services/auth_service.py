from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from biogestor.auth.roles import Role
from biogestor.core.security import verify_password
from biogestor.db.models.user import User
from biogestor.repositories.user_repository import UserRepository
from biogestor.services.audit_service import log_action


@dataclass(frozen=True)
class AuthResult:
    success: bool
    user: User | None = None
    reason: str | None = None


class AuthService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def has_users(self) -> bool:
        with self._session_factory() as session:
            repository = UserRepository(session)
            return repository.count_users() > 0

    def authenticate(self, username: str, password: str) -> AuthResult:
        normalized_username = username.strip()
        if not normalized_username:
            return AuthResult(success=False, reason="Usuario vacio.")

        with self._session_factory() as session:
            repository = UserRepository(session)
            user = repository.get_by_username(normalized_username)
            if user is None or not user.is_active:
                log_action(
                    session,
                    username=normalized_username,
                    module="ADMIN",
                    section="AUTH",
                    screen="LOGIN",
                    action="LOGIN",
                    entity="User",
                    entity_id=normalized_username,
                    description="Intento de login con usuario inexistente o inactivo.",
                    before_data=None,
                    after_data={"success": False},
                )
                session.commit()
                return AuthResult(success=False, reason="Credenciales invalidas.")

            if not verify_password(password, user.password_hash):
                log_action(
                    session,
                    username=normalized_username,
                    module="ADMIN",
                    section="AUTH",
                    screen="LOGIN",
                    action="LOGIN",
                    entity="User",
                    entity_id=str(user.id),
                    description="Intento de login con password incorrecta.",
                    before_data=None,
                    after_data={"success": False},
                )
                session.commit()
                return AuthResult(success=False, reason="Credenciales invalidas.")

            log_action(
                session,
                username=normalized_username,
                module="ADMIN",
                section="AUTH",
                screen="LOGIN",
                action="LOGIN",
                entity="User",
                entity_id=str(user.id),
                description="Login correcto.",
                before_data=None,
                after_data={"success": True, "role": user.role},
            )
            session.expunge(user)
            session.commit()
            return AuthResult(success=True, user=user)

    def create_user(self, username: str, password: str, role: Role, created_by: str = "system") -> User:
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("username vacio")
        if len(password) < 8:
            raise ValueError("password demasiado corta")

        with self._session_factory() as session:
            repository = UserRepository(session)
            if repository.get_by_username(normalized_username) is not None:
                raise ValueError("usuario ya existe")

            user = repository.create_user(
                username=normalized_username,
                password=password,
                role=role,
            )
            session.flush()
            log_action(
                session,
                username=created_by,
                module="ADMIN",
                section="AUTH",
                screen="USERS",
                action="CREATE",
                entity="User",
                entity_id=str(user.id),
                description=f"Alta de usuario con rol {role.value}.",
                before_data=None,
                after_data={"username": user.username, "role": user.role},
            )
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user
