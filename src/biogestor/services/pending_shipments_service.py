from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from biogestor.services.goma_seca_service import GomaSecaService


@dataclass(frozen=True)
class PendingShipmentItem:
    key: str
    label: str
    description: str
    lot_count: int
    kg_total: float
    latest_production_date: date
    lots: tuple[str, ...]


class PendingShipmentsService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._goma_seca_service = GomaSecaService(session_factory)

    def list_pending_products(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PendingShipmentItem]:
        start_date = date_from or date(2026, 1, 1)
        end_date = date_to or date.today()
        items: list[PendingShipmentItem] = []

        goma_seca_records = self._goma_seca_service.search(date_from=start_date, date_to=end_date)
        if goma_seca_records:
            ordered_records = sorted(
                goma_seca_records,
                key=lambda item: (item.production_date, item.finision_number, item.lot_code),
            )
            items.append(
                PendingShipmentItem(
                    key="goma_seca_f1620",
                    label="GOMA SECA F1620",
                    description="Producciones pendientes de revisión de envío.",
                    lot_count=len(ordered_records),
                    kg_total=sum(item.kg_produced for item in ordered_records),
                    latest_production_date=max(item.production_date for item in ordered_records),
                    lots=tuple(item.lot_code for item in ordered_records),
                )
            )

        return items
