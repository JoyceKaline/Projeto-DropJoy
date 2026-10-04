from datetime import datetime, timezone
import secrets
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    MarketplaceAccount,
    MarketplaceListing,
    MarketplaceOAuthCredential,
    Product,
    User,
)
from ..core.auth import get_current_user, require_roles
from ..core.config import get_settings
from ..marketplaces.registry import marketplace_for
from ..services.ai import local_listing
from ..services.audit import audit
from ..services.marketplace_oauth import (
    access_token,
    create_oauth_session,
    consume_oauth_session,
    credential_for_account,
    credential_status,
    mark_oauth_session_used,
    refresh_token,
    upsert_oauth_credential,
)

router = APIRouter(prefix="/api/marketplaces", tags=["marketplaces"])
settings = get_settings()

class AccountCreate(BaseModel):
    provider: str
    external_account_id: str | None = Field(default=None, max_length=160)
    display_name: str = Field(min_length=2, max_length=160)

class ListingCreate(BaseModel):
    account_id: int
    product_id: int
    price: float = Field(gt=0)

VALID_PROVIDERS = {"demo", "shopee", "mercadolivre"}

def _frontend_redirect(**params) -> RedirectResponse:
    base = settings.frontend_base_url.rstrip("/") + "/"
    return RedirectResponse(base + "?" + urlencode(params), status_code=302)

@router.get("")
def overview(user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    accounts = session.scalars(
        select(MarketplaceAccount)
        .where(MarketplaceAccount.tenant_id == user.tenant_id)
        .order_by(MarketplaceAccount.provider)
    ).all()
    listings = session.scalars(
        select(MarketplaceListing)
        .where(MarketplaceListing.tenant_id == user.tenant_id)
        .order_by(MarketplaceListing.id.desc())
    ).all()

    account_rows = []
    for account in accounts:
        connector = marketplace_for(account.provider)
        app_configured = bool(
            connector and getattr(connector, "app_configured", lambda: connector.configured())()
        )
        oauth = credential_status(credential_for_account(session, account.id)) if account.provider == "mercadolivre" else {
            "connected": False,
            "expires_at": None,
            "expired": None,
        }
        connector_ready = bool(connector and connector.configured())
        if account.provider == "mercadolivre":
            connector_ready = bool(app_configured and oauth["connected"])
        account_rows.append({
            "id": account.id,
            "provider": account.provider,
            "external_account_id": account.external_account_id,
            "display_name": account.display_name,
            "status": account.status,
            "connector_configured": connector_ready,
            "app_configured": app_configured,
            "oauth_connected": oauth["connected"],
            "token_expires_at": oauth.get("expires_at"),
            "token_expired": oauth.get("expired"),
        })

    return {
        "accounts": account_rows,
        "listings": [{
            "id": item.id,
            "account_id": item.marketplace_account_id,
            "product_id": item.product_id,
            "external_listing_id": item.external_listing_id,
            "status": item.status,
            "price": item.price,
            "published_at": item.published_at.isoformat() if item.published_at else None,
        } for item in listings],
    }

@router.post("/accounts", status_code=201)
def create_account(
    payload: AccountCreate,
    admin: User = Depends(require_roles("owner", "admin")),
    session: Session = Depends(get_db),
):
    provider = payload.provider.lower().strip()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(400, "Marketplace ainda não suportado")

    external_id = (payload.external_account_id or "").strip()
    if provider == "mercadolivre" and not external_id:
        external_id = "pending-" + secrets.token_hex(8)
    if provider != "mercadolivre" and not external_id:
        raise HTTPException(400, "ID da conta/loja é obrigatório para este marketplace")

    exists = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.tenant_id == admin.tenant_id,
        MarketplaceAccount.provider == provider,
        MarketplaceAccount.external_account_id == external_id,
    ))
    if exists:
        raise HTTPException(409, "Conta já cadastrada")

    connector = marketplace_for(provider)
    app_configured = bool(
        connector and getattr(connector, "app_configured", lambda: connector.configured())()
    )

    if provider == "demo":
        status_value = "connected"
        configured_at = datetime.now(timezone.utc)
    elif provider == "mercadolivre":
        status_value = "pending_authorization" if app_configured else "pending_credentials"
        configured_at = None
    else:
        ready = bool(connector and connector.configured())
        status_value = "connected" if ready else "pending_credentials"
        configured_at = datetime.now(timezone.utc) if ready else None

    account = MarketplaceAccount(
        tenant_id=admin.tenant_id,
        provider=provider,
        external_account_id=external_id,
        display_name=payload.display_name,
        status=status_value,
        configured_at=configured_at,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    audit(
        session,
        tenant_id=admin.tenant_id,
        user=admin,
        action="marketplace.account_created",
        entity_type="marketplace_account",
        entity_id=account.id,
        details={"provider": provider},
    )
    return {"id": account.id, "provider": account.provider, "status": account.status}

@router.post("/mercadolivre/accounts/{account_id}/connect")
def connect_mercadolivre(
    account_id: int,
    admin: User = Depends(require_roles("owner", "admin")),
    session: Session = Depends(get_db),
):
    account = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.id == account_id,
        MarketplaceAccount.tenant_id == admin.tenant_id,
        MarketplaceAccount.provider == "mercadolivre",
    ))
    if not account:
        raise HTTPException(404, "Conta Mercado Livre não encontrada")

    connector = marketplace_for("mercadolivre")
    if not connector or not connector.app_configured():
        raise HTTPException(
            409,
            "Configure MELI_ENABLED=true, MELI_CLIENT_ID, MELI_CLIENT_SECRET e MELI_REDIRECT_URI antes de conectar.",
        )

    state, challenge = create_oauth_session(
        session,
        account_id=account.id,
        tenant_id=admin.tenant_id,
        user_id=admin.id,
        provider="mercadolivre",
    )
    account.status = "authorizing"
    session.commit()

    audit(
        session,
        tenant_id=admin.tenant_id,
        user=admin,
        action="marketplace.oauth_started",
        entity_type="marketplace_account",
        entity_id=account.id,
        details={"provider": "mercadolivre"},
    )
    return {"authorization_url": connector.authorization_url(state=state, code_challenge=challenge)}

@router.get("/mercadolivre/callback", include_in_schema=False)
def mercadolivre_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: Session = Depends(get_db),
):
    if error:
        return _frontend_redirect(marketplace="mercadolivre", oauth_error=error)
    if not code or not state:
        return _frontend_redirect(marketplace="mercadolivre", oauth_error="missing_code_or_state")

    consumed = consume_oauth_session(session, state=state, provider="mercadolivre")
    if not consumed:
        return _frontend_redirect(marketplace="mercadolivre", oauth_error="invalid_or_expired_state")

    oauth_session, verifier = consumed
    account = session.get(MarketplaceAccount, oauth_session.marketplace_account_id)
    user = session.get(User, oauth_session.user_id)
    if not account or account.tenant_id != oauth_session.tenant_id or account.provider != "mercadolivre":
        return _frontend_redirect(marketplace="mercadolivre", oauth_error="account_mismatch")

    connector = marketplace_for("mercadolivre")
    try:
        token_data = connector.exchange_code(code=code, code_verifier=verifier)
        if not token_data.get("access_token") or not token_data.get("user_id"):
            raise RuntimeError("Resposta OAuth sem access_token/user_id")
        credential = upsert_oauth_credential(session, account_id=account.id, token_data=token_data)
        account.external_account_id = credential.external_user_id
        account.status = "connected"
        account.configured_at = datetime.now(timezone.utc)
        session.commit()
        mark_oauth_session_used(session, oauth_session)

        try:
            profile = connector.user_info(access_token=access_token(credential))
            nickname = profile.get("nickname")
            if nickname and account.display_name.lower().startswith("mercado livre"):
                account.display_name = f"Mercado Livre - {nickname}"
                session.commit()
        except Exception:
            pass

        audit(
            session,
            tenant_id=account.tenant_id,
            user=user,
            action="marketplace.oauth_connected",
            entity_type="marketplace_account",
            entity_id=account.id,
            details={"provider": "mercadolivre", "external_user_id": account.external_account_id},
        )
        return _frontend_redirect(marketplace="mercadolivre", connected="1")
    except (httpx.HTTPError, RuntimeError):
        account.status = "oauth_error"
        session.commit()
        return _frontend_redirect(marketplace="mercadolivre", oauth_error="token_exchange_failed")

@router.post("/mercadolivre/accounts/{account_id}/refresh")
def refresh_mercadolivre(
    account_id: int,
    admin: User = Depends(require_roles("owner", "admin")),
    session: Session = Depends(get_db),
):
    account = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.id == account_id,
        MarketplaceAccount.tenant_id == admin.tenant_id,
        MarketplaceAccount.provider == "mercadolivre",
    ))
    if not account:
        raise HTTPException(404, "Conta Mercado Livre não encontrada")

    credential = credential_for_account(session, account.id)
    if not credential:
        raise HTTPException(409, "Conta ainda não autorizada no Mercado Livre")
    current_refresh = refresh_token(credential)
    if not current_refresh:
        raise HTTPException(409, "Refresh token não disponível; reconecte a conta")

    connector = marketplace_for("mercadolivre")
    try:
        token_data = connector.refresh_access_token(refresh_token=current_refresh)
        upsert_oauth_credential(session, account_id=account.id, token_data=token_data)
        account.status = "connected"
        session.commit()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "O Mercado Livre rejeitou a renovação do token") from exc

    audit(
        session,
        tenant_id=admin.tenant_id,
        user=admin,
        action="marketplace.oauth_refreshed",
        entity_type="marketplace_account",
        entity_id=account.id,
        details={"provider": "mercadolivre"},
    )
    return {"status": "ok"}

@router.post("/mercadolivre/accounts/{account_id}/disconnect")
def disconnect_mercadolivre(
    account_id: int,
    admin: User = Depends(require_roles("owner", "admin")),
    session: Session = Depends(get_db),
):
    account = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.id == account_id,
        MarketplaceAccount.tenant_id == admin.tenant_id,
        MarketplaceAccount.provider == "mercadolivre",
    ))
    if not account:
        raise HTTPException(404, "Conta Mercado Livre não encontrada")
    credential = credential_for_account(session, account.id)
    if credential:
        session.delete(credential)
    account.status = "pending_authorization" if marketplace_for("mercadolivre").app_configured() else "pending_credentials"
    account.configured_at = None
    session.commit()
    audit(
        session,
        tenant_id=admin.tenant_id,
        user=admin,
        action="marketplace.oauth_disconnected",
        entity_type="marketplace_account",
        entity_id=account.id,
        details={"provider": "mercadolivre"},
    )
    return {"status": "ok"}

@router.post("/listings", status_code=201)
def create_listing(
    payload: ListingCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    account = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.id == payload.account_id,
        MarketplaceAccount.tenant_id == user.tenant_id,
    ))
    product = session.get(Product, payload.product_id)
    if not account or not product:
        raise HTTPException(404, "Conta ou produto não encontrado")
    exists = session.scalar(select(MarketplaceListing).where(
        MarketplaceListing.tenant_id == user.tenant_id,
        MarketplaceListing.marketplace_account_id == account.id,
        MarketplaceListing.product_id == product.id,
    ))
    if exists:
        raise HTTPException(409, "Já existe uma listagem desse produto nessa conta")
    listing = MarketplaceListing(
        tenant_id=user.tenant_id,
        marketplace_account_id=account.id,
        product_id=product.id,
        status="draft",
        price=payload.price,
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    audit(
        session,
        tenant_id=user.tenant_id,
        user=user,
        action="marketplace.listing_created",
        entity_type="marketplace_listing",
        entity_id=listing.id,
    )
    return {"id": listing.id, "status": listing.status}

@router.post("/listings/{listing_id}/publish")
def publish_listing(
    listing_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    listing = session.scalar(select(MarketplaceListing).where(
        MarketplaceListing.id == listing_id,
        MarketplaceListing.tenant_id == user.tenant_id,
    ))
    if not listing:
        raise HTTPException(404, "Listagem não encontrada")
    account = session.get(MarketplaceAccount, listing.marketplace_account_id)
    product = session.get(Product, listing.product_id)
    connector = marketplace_for(account.provider) if account else None
    if not connector:
        raise HTTPException(400, "Conector de marketplace inexistente")
    if account.provider == "mercadolivre" and not credential_for_account(session, account.id):
        raise HTTPException(409, "Conecte a conta do Mercado Livre antes de publicar")
    if not connector.configured():
        raise HTTPException(409, "Marketplace ainda não está configurado com credenciais reais")

    base = local_listing(product)
    try:
        result = connector.publish(
            title=base["title"],
            description=base["description"],
            price=listing.price,
            external_account_id=account.external_account_id,
        )
    except NotImplementedError as exc:
        raise HTTPException(501, str(exc))

    listing.external_listing_id = result.external_listing_id
    listing.status = result.status
    listing.published_at = datetime.now(timezone.utc)
    session.commit()
    audit(
        session,
        tenant_id=user.tenant_id,
        user=user,
        action="marketplace.listing_published",
        entity_type="marketplace_listing",
        entity_id=listing.id,
        details={"provider": account.provider},
    )
    return {"id": listing.id, "status": listing.status, "external_listing_id": listing.external_listing_id}
