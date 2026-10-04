from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import MarketplaceAccount, MarketplaceListing, Product, User
from ..core.auth import get_current_user, require_roles
from ..marketplaces.registry import marketplace_for
from ..services.ai import local_listing
from ..services.audit import audit

router = APIRouter(prefix="/api/marketplaces", tags=["marketplaces"])

class AccountCreate(BaseModel):
    provider: str
    external_account_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=2, max_length=160)

class ListingCreate(BaseModel):
    account_id: int
    product_id: int
    price: float = Field(gt=0)

VALID_PROVIDERS = {"demo", "shopee", "mercadolivre"}

@router.get("")
def overview(user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    accounts = session.scalars(select(MarketplaceAccount).where(MarketplaceAccount.tenant_id == user.tenant_id).order_by(MarketplaceAccount.provider)).all()
    listings = session.scalars(select(MarketplaceListing).where(MarketplaceListing.tenant_id == user.tenant_id).order_by(MarketplaceListing.id.desc())).all()
    account_rows = []
    for a in accounts:
        connector = marketplace_for(a.provider)
        account_rows.append({
            "id": a.id,
            "provider": a.provider,
            "external_account_id": a.external_account_id,
            "display_name": a.display_name,
            "status": a.status,
            "connector_configured": bool(connector and connector.configured()),
            "app_configured": bool(connector and getattr(connector, "app_configured", lambda: connector.configured())()),
        })
    return {
        "accounts": account_rows,
        "listings": [{"id": x.id, "account_id": x.marketplace_account_id, "product_id": x.product_id, "external_listing_id": x.external_listing_id, "status": x.status, "price": x.price, "published_at": x.published_at.isoformat() if x.published_at else None} for x in listings],
    }

@router.post("/accounts", status_code=201)
def create_account(payload: AccountCreate, admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db)):
    provider = payload.provider.lower().strip()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(400, "Marketplace ainda não suportado")
    exists = session.scalar(select(MarketplaceAccount).where(MarketplaceAccount.tenant_id == admin.tenant_id, MarketplaceAccount.provider == provider, MarketplaceAccount.external_account_id == payload.external_account_id))
    if exists:
        raise HTTPException(409, "Conta já cadastrada")
    connector = marketplace_for(provider)
    account = MarketplaceAccount(tenant_id=admin.tenant_id, provider=provider, external_account_id=payload.external_account_id, display_name=payload.display_name, status="connected" if connector and connector.configured() else "pending_credentials", configured_at=datetime.now(timezone.utc) if connector and connector.configured() else None)
    session.add(account); session.commit(); session.refresh(account)
    audit(session, tenant_id=admin.tenant_id, user=admin, action="marketplace.account_created", entity_type="marketplace_account", entity_id=account.id, details={"provider": provider})
    return {"id": account.id, "provider": account.provider, "status": account.status}

@router.post("/listings", status_code=201)
def create_listing(payload: ListingCreate, user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    account = session.scalar(select(MarketplaceAccount).where(MarketplaceAccount.id == payload.account_id, MarketplaceAccount.tenant_id == user.tenant_id))
    product = session.get(Product, payload.product_id)
    if not account or not product:
        raise HTTPException(404, "Conta ou produto não encontrado")
    exists = session.scalar(select(MarketplaceListing).where(MarketplaceListing.tenant_id == user.tenant_id, MarketplaceListing.marketplace_account_id == account.id, MarketplaceListing.product_id == product.id))
    if exists:
        raise HTTPException(409, "Já existe uma listagem desse produto nessa conta")
    listing = MarketplaceListing(tenant_id=user.tenant_id, marketplace_account_id=account.id, product_id=product.id, status="draft", price=payload.price)
    session.add(listing); session.commit(); session.refresh(listing)
    audit(session, tenant_id=user.tenant_id, user=user, action="marketplace.listing_created", entity_type="marketplace_listing", entity_id=listing.id)
    return {"id": listing.id, "status": listing.status}

@router.post("/listings/{listing_id}/publish")
def publish_listing(listing_id: int, user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    listing = session.scalar(select(MarketplaceListing).where(MarketplaceListing.id == listing_id, MarketplaceListing.tenant_id == user.tenant_id))
    if not listing:
        raise HTTPException(404, "Listagem não encontrada")
    account = session.get(MarketplaceAccount, listing.marketplace_account_id)
    product = session.get(Product, listing.product_id)
    connector = marketplace_for(account.provider) if account else None
    if not connector:
        raise HTTPException(400, "Conector de marketplace inexistente")
    if not connector.configured():
        raise HTTPException(409, "Marketplace ainda não está configurado com credenciais reais")
    base = local_listing(product)
    try:
        result = connector.publish(title=base["title"], description=base["description"], price=listing.price, external_account_id=account.external_account_id)
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc))
    listing.external_listing_id = result.external_listing_id
    listing.status = result.status
    listing.published_at = datetime.now(timezone.utc)
    session.commit()
    audit(session, tenant_id=user.tenant_id, user=user, action="marketplace.listing_published", entity_type="marketplace_listing", entity_id=listing.id, details={"provider": account.provider})
    return {"id": listing.id, "status": listing.status, "external_listing_id": listing.external_listing_id}
