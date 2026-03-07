from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "BioGestor"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://biogestor_user:change_me@localhost:5432/biogestor",
        ),
    )

