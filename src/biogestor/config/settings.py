from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

_BASE_DIR = Path(__file__).resolve().parents[3]
_DEFAULT_SQLITE_PATH = _BASE_DIR / "data" / "biogestor-dev.db"


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str


def _default_database_url() -> str:
    configured_url = os.getenv("DATABASE_URL")
    if configured_url:
        return configured_url

    _DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_SQLITE_PATH.as_posix()}"


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "BioGestor"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=_default_database_url(),
    )
