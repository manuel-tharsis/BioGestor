from biogestor.db.base import Base
from biogestor.db.session import engine
from biogestor.db import models  # noqa: F401


def create_all() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_all()

