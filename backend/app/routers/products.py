from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from ..db import get_db
from ..models import Product, Offer, Tenant
from ..core.tenant import current_tenant
from ..services.scoring import dropjoy_score, offer_payload
from ..core.config import get_settings

router = APIRouter(prefix="/api/products", tags=["products"])
settings = get_settings()

@router.get("")
def products(session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    ps = session.scalars(select(Product).options(selectinload(Product.offers).selectinload(Offer.supplier))).all()
    return [{"id": p.id, "name": p.name, "category": p.category, "sale_price": p.sale_price, "best_score": max((dropjoy_score(p, o) for o in p.offers), default=0), "offers": len(p.offers)} for p in ps]

@router.get("/{product_id}")
def product_detail(product_id: int, session: Session = Depends(get_db), tenant: Tenant = Depends(current_tenant)):
    p = session.scalar(select(Product).where(Product.id == product_id).options(selectinload(Product.offers).selectinload(Offer.supplier), selectinload(Product.offers).selectinload(Offer.history)))
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    offers = []
    for o in p.offers:
        x = offer_payload(o)
        x["history"] = [{"captured_at": h.captured_at.isoformat(), "cost": h.cost, "stock": h.stock} for h in sorted(o.history, key=lambda h: h.captured_at)]
        offers.append(x)
    offers.sort(key=lambda x: x["score"], reverse=True)
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "sale_price": p.sale_price,
        "competition_score": round(p.competition_score * 100),
        "recommendation": offers[0]["supplier"] if offers else None,
        "offers": offers,
        "fee_assumption": {"percent": settings.marketplace_percent_fee * 100, "fixed": settings.marketplace_fixed_fee, "warning": "Parâmetros demonstrativos; valide as tarifas atuais do marketplace antes de decisões comerciais."},
    }
