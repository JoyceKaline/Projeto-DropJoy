from fastapi import Header, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Tenant
from .config import get_settings

settings = get_settings()

def current_tenant(x_tenant_slug: str | None = Header(default=None), session: Session = Depends(get_db)) -> Tenant:
    slug = x_tenant_slug or settings.default_tenant_slug
    tenant = session.scalar(select(Tenant).where(Tenant.slug == slug, Tenant.active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado")
    return tenant
