from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from ..db import get_db
from ..models import Product, Offer, Supplier, Tenant, TenantSupplier
from ..core.tenant import current_tenant
from ..services.scoring import dropjoy_score, offer_payload
from ..services.tenant_scope import enabled_supplier_ids

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/dashboard")
def dashboard(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    allowed = enabled_supplier_ids(session, tenant.id)
    products = session.scalars(select(Product).options(selectinload(Product.offers).selectinload(Offer.supplier))).all()
    items = []
    for p in products:
        offers = [o for o in p.offers if o.supplier_id in allowed]
        if not offers:
            continue
        best = max(offers, key=lambda o: dropjoy_score(p, o))
        item = offer_payload(best)
        item.update({"product": p.name, "category": p.category, "offers_count": len(offers)})
        items.append(item)
    items.sort(key=lambda x: x["score"], reverse=True)
    return {
        "tenant": {"name": tenant.name, "slug": tenant.slug},
        "metrics": {
            "products": len(items),
            "opportunities": sum(i["score"] >= 75 for i in items),
            "suppliers": session.scalar(select(func.count(TenantSupplier.id)).where(TenantSupplier.tenant_id == tenant.id, TenantSupplier.enabled.is_(True))),
            "average_margin": round(sum(i["margin"] for i in items) / len(items), 1) if items else 0,
            "low_stock": sum(i["stock"] < 20 for i in items),
        },
        "opportunities": items,
    }
