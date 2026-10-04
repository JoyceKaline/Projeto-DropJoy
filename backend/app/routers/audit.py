import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import AuditLog, User
from ..core.auth import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def list_audit(admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db), limit: int = 100):
    limit = max(1, min(limit, 500))
    rows = session.scalars(select(AuditLog).where(AuditLog.tenant_id == admin.tenant_id).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{
        "id": x.id,
        "action": x.action,
        "entity_type": x.entity_type,
        "entity_id": x.entity_id,
        "user_id": x.user_id,
        "details": json.loads(x.details) if x.details else None,
        "created_at": x.created_at.isoformat(),
    } for x in rows]
