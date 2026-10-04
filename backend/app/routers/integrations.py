from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Tenant
from ..core.tenant import current_tenant
from ..services.sync import integration_status, demo_sync
from ..connectors.dropify import DropifyConnector

router = APIRouter(prefix="/api/integrations", tags=["integrations"])

@router.get("")
def integrations(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    return {"tenant": tenant.slug, "integrations": integration_status(session, tenant.id)}

@router.post("/demo/sync")
def sync_demo(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    return demo_sync(session, tenant.id)

@router.get("/dropify/status")
def dropify_status(tenant: Tenant = Depends(current_tenant)):
    c = DropifyConnector()
    return {
        "supplier": "Dropify",
        "configured": c.configured(),
        "mode": "api" if c.configured() else "demo",
        "message": "Credenciais detectadas." if c.configured() else "Aguardando credenciais homologadas e mapeamento do schema real da API.",
    }

@router.post("/dropify/sync")
def dropify_sync(tenant: Tenant = Depends(current_tenant)):
    c = DropifyConnector()
    if not c.configured():
        raise HTTPException(status_code=409, detail="Dropify ainda não configurada. Use o modo demo ou configure as credenciais no .env.")
    try:
        items = c.list_items()
        return {"status": "ok", "items": len(items)}
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
