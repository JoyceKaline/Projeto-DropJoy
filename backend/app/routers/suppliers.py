from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Supplier, Tenant
from ..core.tenant import current_tenant

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

@router.get("")
def suppliers(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    return [{"id": x.id, "name": x.name, "slug": x.slug, "integration_type": x.integration_type, "reliability": round(x.reliability * 100)} for x in session.scalars(select(Supplier)).all()]
