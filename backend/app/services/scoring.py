from ..core.config import get_settings
from ..models import Product, Offer

settings = get_settings()

def finance(product: Product, offer: Offer) -> dict:
    sale = product.sale_price
    fees = sale * settings.marketplace_percent_fee + settings.marketplace_fixed_fee
    profit = sale - fees - offer.cost
    margin = profit / sale if sale else 0
    return {"fees": round(fees, 2), "profit": round(profit, 2), "margin": round(margin * 100, 1)}

def dropjoy_score(product: Product, offer: Offer) -> int:
    f = finance(product, offer)
    margin = max(0, f["margin"] / 100)
    margin_score = min(1, margin / .35)
    stock_score = min(1, offer.stock / 100)
    speed_score = max(0, min(1, 1 - (offer.shipping_hours - 24) / 72))
    raw = (.35 * margin_score + .25 * product.competition_score + .20 * stock_score + .10 * speed_score + .10 * offer.supplier.reliability)
    return round(100 * raw)

def offer_payload(offer: Offer) -> dict:
    f = finance(offer.product, offer)
    return {
        "offer_id": offer.id,
        "product_id": offer.product.id,
        "supplier_id": offer.supplier.id,
        "supplier": offer.supplier.name,
        "supplier_slug": offer.supplier.slug,
        "cost": offer.cost,
        "sale_price": offer.product.sale_price,
        "stock": offer.stock,
        "shipping_hours": offer.shipping_hours,
        "fees": f["fees"],
        "profit": f["profit"],
        "margin": f["margin"],
        "score": dropjoy_score(offer.product, offer),
        "reliability": round(offer.supplier.reliability * 100),
        "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
    }
