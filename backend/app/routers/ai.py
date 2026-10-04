from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Product, User
from ..core.auth import get_current_user
from ..services.ai import generate_listing
from ..services.audit import audit

router = APIRouter(prefix="/api/ai", tags=["ai"])

class GenerateRequest(BaseModel):
    product_id: int
    notes: str | None = Field(default=None, max_length=1500)

@router.post("/listing")
def generate(payload: GenerateRequest, user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    product = session.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Produto não encontrado")
    try:
        result = generate_listing(product, payload.notes)
    except Exception as exc:
        raise HTTPException(502, f"Falha ao gerar anúncio: {type(exc).__name__}")
    audit(session, tenant_id=user.tenant_id, user=user, action="ai.listing_generated", entity_type="product", entity_id=product.id, details={"provider": result.get("provider")})
    return result
