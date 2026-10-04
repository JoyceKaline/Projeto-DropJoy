from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Supplier, Tenant, TenantSupplier, User
from ..core.tenant import current_tenant
from ..core.auth import require_roles
from ..services.audit import audit

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

class SupplierPatch(BaseModel):
    enabled: bool | None = None
    mode: str | None = None

@router.get("")
def suppliers(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    links = {x.supplier_id: x for x in session.scalars(select(TenantSupplier).where(TenantSupplier.tenant_id == tenant.id)).all()}
    result = []
    for supplier in session.scalars(select(Supplier).order_by(Supplier.name)).all():
        link = links.get(supplier.id)
        result.append({
            "id": supplier.id,
            "name": supplier.name,
            "slug": supplier.slug,
            "integration_type": supplier.integration_type,
            "reliability": round(supplier.reliability * 100),
            "enabled": bool(link and link.enabled),
            "mode": link.mode if link else "off",
        })
    return result

@router.patch("/{supplier_id}")
def update_supplier(supplier_id: int, payload: SupplierPatch, admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db)):
    supplier = session.get(Supplier, supplier_id)
    if not supplier:
        raise HTTPException(404, "Fornecedor não encontrado")
    link = session.scalar(select(TenantSupplier).where(TenantSupplier.tenant_id == admin.tenant_id, TenantSupplier.supplier_id == supplier_id))
    if not link:
        link = TenantSupplier(tenant_id=admin.tenant_id, supplier_id=supplier_id, enabled=False, mode="demo")
        session.add(link)
    if payload.enabled is not None:
        link.enabled = payload.enabled
    if payload.mode is not None:
        if payload.mode not in {"demo", "api"}:
            raise HTTPException(400, "Modo inválido")
        link.mode = payload.mode
    session.commit()
    audit(session, tenant_id=admin.tenant_id, user=admin, action="supplier.updated", entity_type="supplier", entity_id=supplier.id, details={"enabled": link.enabled, "mode": link.mode})
    return {"id": supplier.id, "enabled": link.enabled, "mode": link.mode}
