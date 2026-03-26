from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from biogestor.db.base import Base


class SolventWeekMetric(Base):
    __tablename__ = "solvent_week_metrics"
    __table_args__ = (
        UniqueConstraint("solvent_name", "week_start", name="uq_solvent_week_metric"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    solvent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    purchases_liters: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stock_liters: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    consumed_liters: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
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
