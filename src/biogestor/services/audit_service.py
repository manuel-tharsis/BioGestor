from typing import Any

from sqlalchemy.orm import Session

from biogestor.db.models.audit_log import AuditLog


def log_action(
    session: Session,
    *,
    username: str,
    module: str,
    section: str,
    screen: str,
    action: str,
    entity: str,
    entity_id: str,
    description: str,
    before_data: dict[str, Any] | None = None,
    after_data: dict[str, Any] | None = None,
) -> AuditLog:
    event = AuditLog(
        username=username,
        module=module,
        section=section,
        screen=screen,
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
        before_data=before_data,
        after_data=after_data,
    )
    session.add(event)
    return event

