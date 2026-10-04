from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Supplier, TenantSupplier, Offer, OfferHistory
from ..connectors.registry import connector_for

class IntegrationNotReady(RuntimeError):
    pass

def integration_status(session: Session, tenant_id: int) -> list[dict]:
    suppliers = session.scalars(select(Supplier).order_by(Supplier.name)).all()
    links = {x.supplier_id: x for x in session.scalars(select(TenantSupplier).where(TenantSupplier.tenant_id == tenant_id)).all()}
    result = []
    for supplier in suppliers:
        link = links.get(supplier.id)
        connector = connector_for(supplier.slug)
        configured = connector.configured() if connector else False
        result.append({
            "supplier_id": supplier.id,
            "name": supplier.name,
            "slug": supplier.slug,
            "integration_type": supplier.integration_type,
            "enabled": bool(link and link.enabled),
            "mode": link.mode if link else "off",
            "configured": configured if supplier.slug == "dropify" else bool(link and link.mode == "demo"),
            "last_sync_at": link.last_sync_at.isoformat() if link and link.last_sync_at else None,
        })
    return result

def demo_sync(session: Session, tenant_id: int) -> dict:
    """Atualização determinística para demonstrar snapshots sem API externa."""
    offers = session.scalars(select(Offer).order_by(Offer.id)).all()
    now = datetime.now(timezone.utc)
    changed = 0
    for offer in offers:
        delta_cents = ((offer.id % 3) - 1) * 0.35
        stock_delta = (offer.id % 5) - 2
        offer.cost = round(max(1, offer.cost + delta_cents), 2)
        offer.stock = max(0, offer.stock + stock_delta)
        offer.updated_at = now
        session.add(OfferHistory(offer_id=offer.id, captured_at=now, cost=offer.cost, stock=offer.stock))
        changed += 1
    links = session.scalars(select(TenantSupplier).where(TenantSupplier.tenant_id == tenant_id)).all()
    for link in links:
        if link.mode == "demo":
            link.last_sync_at = now
    session.commit()
    return {"status": "ok", "mode": "demo", "offers_updated": changed, "synced_at": now.isoformat()}
