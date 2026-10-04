from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from ..db import get_db
from ..models import Product, Offer, Supplier, Tenant
from ..core.tenant import current_tenant
from ..services.scoring import dropjoy_score, offer_payload

router = APIRouter(prefix="/api", tags=["dashboard"])

@router.get("/dashboard")
def dashboard(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    products = session.scalars(select(Product).options(selectinload(Product.offers).selectinload(Offer.supplier))).all()
    items = []
    for p in products:
        if not p.offers:
            continue
        best = max(p.offers, key=lambda o: dropjoy_score(p, o))
        item = offer_payload(best)
        item.update({"product": p.name, "category": p.category, "offers_count": len(p.offers)})
        items.append(item)
    items.sort(key=lambda x: x["score"], reverse=True)
    return {
        "tenant": {"name": tenant.name, "slug": tenant.slug},
        "metrics": {
            "products": len(products),
            "opportunities": sum(i["score"] >= 75 for i in items),
            "suppliers": session.scalar(select(func.count(Supplier.id))),
            "average_margin": round(sum(i["margin"] for i in items) / len(items), 1) if items else 0,
            "low_stock": sum(i["stock"] < 20 for i in items),
        },
        "opportunities": items,
    }
