from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, sessionmaker

from biogestor.db.base import Base
from biogestor.db.models.bidon import Bidon
from biogestor.db.session import SessionLocal, engine
from biogestor.db import models  # noqa: F401


DEFAULT_BIDON_PREFIX = "P"
DEFAULT_BIDON_RANGE = range(1, 201)
GOMA_SECA_TABLE = "goma_seca_productions"

GOMA_SECA_MISSING_COLUMNS = {
    "raw_drum_identification": "VARCHAR(32) NOT NULL DEFAULT ''",
    "raw_kg_used": "FLOAT NOT NULL DEFAULT 0",
    "filter_cleanings": "INTEGER NOT NULL DEFAULT 0",
    "day_start_time": "VARCHAR(5) NOT NULL DEFAULT ''",
    "top_temperature": "FLOAT NOT NULL DEFAULT 0",
    "gum_temperature": "FLOAT NOT NULL DEFAULT 0",
    "vacuum": "FLOAT NOT NULL DEFAULT 0",
    "distillation_minutes": "INTEGER NOT NULL DEFAULT 0",
}


def ensure_default_bidones(session_factory: sessionmaker[Session] = SessionLocal) -> int:
    created = 0
    with session_factory() as session:
        existing_identifications = {
            identification
            for (identification,) in session.query(Bidon.identification).all()
        }
        missing_bidones = []
        for number in DEFAULT_BIDON_RANGE:
            identification = f"{DEFAULT_BIDON_PREFIX}{number:03d}"
            if identification in existing_identifications:
                continue
            missing_bidones.append(
                Bidon(
                    identification=identification,
                    status="stock",
                    consumed_in=None,
                    notes="",
                    created_by="system",
                )
            )

        if missing_bidones:
            session.add_all(missing_bidones)
            session.commit()
            created = len(missing_bidones)

    return created


def ensure_goma_seca_schema() -> None:
    inspector = inspect(engine)
    if not inspector.has_table(GOMA_SECA_TABLE):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(GOMA_SECA_TABLE)}
    with engine.begin() as connection:
        for column_name, column_sql in GOMA_SECA_MISSING_COLUMNS.items():
            if column_name in existing_columns:
                continue
            connection.execute(
                text(f"ALTER TABLE {GOMA_SECA_TABLE} ADD COLUMN {column_name} {column_sql}")
            )


def create_all() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_goma_seca_schema()
    ensure_default_bidones()


if __name__ == "__main__":
    create_all()
