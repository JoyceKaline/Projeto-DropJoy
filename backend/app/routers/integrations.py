from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Tenant
from ..core.tenant import current_tenant
from ..services.sync import integration_status, demo_sync
from ..connectors.registry import connector_for

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

@router.get("")
def integrations(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    return {"tenant": tenant.slug, "integrations": integration_status(session, tenant.id)}

@router.post("/demo/sync")
def sync_demo(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    return demo_sync(session, tenant.id)

@router.get("/{supplier_slug}/status")
def connector_status(supplier_slug: str, tenant: Tenant = Depends(current_tenant)):
    connector = connector_for(supplier_slug)
    if not connector:
        raise HTTPException(404, "Conector não encontrado")
    return {"supplier": supplier_slug, "configured": connector.configured(), "mode": "api" if connector.configured() else "demo"}

@router.post("/{supplier_slug}/sync")
def connector_sync(supplier_slug: str, tenant: Tenant = Depends(current_tenant)):
    connector = connector_for(supplier_slug)
    if not connector:
        raise HTTPException(404, "Conector não encontrado")
    if not connector.configured():
        raise HTTPException(409, "Conector ainda não configurado com credenciais reais")
    try:
        items = connector.list_items()
        return {"status": "ok", "supplier": supplier_slug, "items": len(items)}
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc))
