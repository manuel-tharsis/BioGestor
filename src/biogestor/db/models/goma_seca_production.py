from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from biogestor.db.base import Base


class GomaSecaProduction(Base):
    __tablename__ = "goma_seca_productions"
    __table_args__ = (UniqueConstraint("lot_code", name="uq_goma_seca_lot_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    production_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    lot_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    finision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kg_produced: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_percent: Mapped[float] = mapped_column(Float, nullable=False)
    observations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
