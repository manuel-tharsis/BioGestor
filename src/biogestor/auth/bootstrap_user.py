import argparse
import getpass

from biogestor.auth.roles import Role
from biogestor.db import models  # noqa: F401
from biogestor.db.init_db import create_all
from biogestor.db.session import SessionLocal
from biogestor.services.auth_service import AuthService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crear usuario inicial de BioGestor")
    parser.add_argument("--username", required=True, help="Nombre de usuario")
    parser.add_argument(
        "--role",
        choices=[role.value for role in Role],
        default=Role.ADMIN.value,
        help="Rol del usuario",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirmar password: ")
    if password != confirm:
        print("Las passwords no coinciden.")
        return 1

    create_all()
    auth = AuthService(SessionLocal)
    user = auth.create_user(args.username, password, role=Role(args.role), created_by="system")
    print(f"Usuario creado: {user.username} ({user.role})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
