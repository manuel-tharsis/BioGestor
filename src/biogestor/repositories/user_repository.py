from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from biogestor.auth.roles import Role
from biogestor.core.security import hash_password
from biogestor.db.models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_all(self) -> Sequence[User]:
        stmt = select(User).order_by(User.username.asc())
        return self.session.execute(stmt).scalars().all()

    def create_user(self, username: str, password: str, role: Role = Role.OPERATOR) -> User:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role.value,
            is_active=True,
        )
        self.session.add(user)
        return user

