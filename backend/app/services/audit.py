import json
from sqlalchemy.orm import Session
from ..models import AuditLog, User
from ..core.security import utcnow

def audit(session: Session, *, tenant_id: int, user: User | None, action: str, entity_type: str | None = None, entity_id: str | int | None = None, details: dict | None = None) -> None:
    session.add(AuditLog(
        tenant_id=tenant_id,
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        created_at=utcnow(),
    ))
    session.commit()
