from datetime import datetime, timezone
import json
import secrets
from typing import Literal
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
    category_id: str | None = Field(default=None, min_length=4, max_length=40)
    family_name: str | None = Field(default=None, min_length=2, max_length=180)
    condition: Literal["new", "used", "not_specified"] | None = None
    currency_id: str = Field(default="BRL", min_length=3, max_length=10)
    listing_type_id: str | None = Field(default=None, min_length=2, max_length=40)
    available_quantity: int | None = Field(default=None, ge=0)
    pictures: list[str] = Field(default_factory=list, max_length=12)
    attributes: list[dict[str, str | None]] = Field(default_factory=list, max_length=100)
    stock_locations: list[dict[str, str | int]] = Field(default_factory=list, max_length=50)

VALID_PROVIDERS = {"demo", "shopee", "mercadolivre"}

def _frontend_redirect(**params) -> RedirectResponse:
    base = settings.frontend_base_url.rstrip("/") + "/"
    return RedirectResponse(base + "?" + urlencode(params), status_code=302)


def _meli_account(session: Session, *, account_id: int, tenant_id: int) -> MarketplaceAccount:
    account = session.scalar(select(MarketplaceAccount).where(
        MarketplaceAccount.id == account_id,
        MarketplaceAccount.tenant_id == tenant_id,
        MarketplaceAccount.provider == "mercadolivre",
    ))
    if not account:
        raise HTTPException(404, "Conta Mercado Livre não encontrada")
    return account


def _meli_access_token(session: Session, account: MarketplaceAccount) -> str:
    credential = credential_for_account(session, account.id)
    if not credential:
        raise HTTPException(409, "Conecte a conta do Mercado Livre antes de continuar")
    if credential_status(credential)["expired"]:
        current_refresh = refresh_token(credential)
        if not current_refresh:
            raise HTTPException(409, "Token expirado; reconecte a conta do Mercado Livre")
        connector = marketplace_for("mercadolivre")
        try:
            token_data = connector.refresh_access_token(refresh_token=current_refresh)
            credential = upsert_oauth_credential(session, account_id=account.id, token_data=token_data)
        except httpx.HTTPError as exc:
            raise HTTPException(502, "Não foi possível renovar o token do Mercado Livre") from exc
    return access_token(credential)


def _meli_http_error(exc: httpx.HTTPError) -> str:
    if not isinstance(exc, httpx.HTTPStatusError):
        return "Não foi possível comunicar com o Mercado Livre. Tente novamente."
    try:
        body = exc.response.json()
    except ValueError:
        return "O Mercado Livre rejeitou a solicitação."
    message = body.get("message") or body.get("error") or "O Mercado Livre rejeitou a solicitação."
    causes = body.get("cause") or []
    details = [str(cause.get("message") or cause.get("code")) for cause in causes if isinstance(cause, dict)]
    return (str(message) + (": " + "; ".join(details) if details else ""))[:2000]

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
            "category_id": item.category_id,
            "family_name": item.family_name,
            "condition": item.condition,
            "currency_id": item.currency_id,
            "listing_type_id": item.listing_type_id,
            "available_quantity": item.available_quantity,
            "user_product_id": item.user_product_id,
            "publication_error": item.publication_error,
            "published_at": item.published_at.isoformat() if item.published_at else None,
        } for item in listings],
    }


@router.get("/mercadolivre/accounts/{account_id}/categories/predict")
def predict_mercadolivre_category(
    account_id: int,
    q: str = Query(min_length=2, max_length=180),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    account = _meli_account(session, account_id=account_id, tenant_id=user.tenant_id)
    connector = marketplace_for("mercadolivre")
    try:
        return {"results": connector.predict_categories(
            query=q,
            access_token=_meli_access_token(session, account),
        )}
    except httpx.HTTPError as exc:
        raise HTTPException(502, _meli_http_error(exc)) from exc


@router.get("/mercadolivre/accounts/{account_id}/categories/{category_id}")
def mercadolivre_category_requirements(
    account_id: int,
    category_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    account = _meli_account(session, account_id=account_id, tenant_id=user.tenant_id)
    connector = marketplace_for("mercadolivre")
    token = _meli_access_token(session, account)
    try:
        category = connector.category(category_id=category_id, access_token=token)
        attributes = connector.category_attributes(category_id=category_id, access_token=token)
        listing_types = connector.available_listing_types(
            external_account_id=account.external_account_id,
            category_id=category_id,
            access_token=token,
        )
        profile = connector.user_info(access_token=token)
        seller_tags = profile.get("tags") or []
        user_product_seller = "user_product_seller" in seller_tags
        warehouse_management = "warehouse_management" in seller_tags
        stock_locations = connector.stock_locations(
            external_account_id=account.external_account_id,
            access_token=token,
        ) if warehouse_management else []
    except httpx.HTTPError as exc:
        raise HTTPException(502, _meli_http_error(exc)) from exc
    return {
        "category": category,
        "attributes": attributes,
        "listing_types": listing_types,
        "user_product_seller": user_product_seller,
        "warehouse_management": warehouse_management,
        "stock_locations": stock_locations,
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
    if account.provider == "mercadolivre":
        required = {
            "category_id": payload.category_id,
            "family_name": payload.family_name,
            "condition": payload.condition,
            "listing_type_id": payload.listing_type_id,
            "available_quantity": payload.available_quantity,
            "pictures": payload.pictures,
            "attributes": payload.attributes,
        }
        missing = [name for name, value in required.items() if value is None or value == [] or value == ""]
        if missing:
            raise HTTPException(422, "Campos obrigatórios do Mercado Livre: " + ", ".join(missing))
        if not payload.category_id.startswith("MLB"):
            raise HTTPException(422, "A categoria deve pertencer ao site brasileiro (prefixo MLB)")
        if any(not picture.startswith(("https://", "http://")) for picture in payload.pictures):
            raise HTTPException(422, "As imagens devem usar URLs HTTP ou HTTPS públicas")
        for attribute in payload.attributes:
            if not attribute.get("id") or not (attribute.get("value_id") or attribute.get("value_name")):
                raise HTTPException(422, "Cada atributo precisa de id e value_id ou value_name")
        for location in payload.stock_locations:
            if not location.get("store_id") or not location.get("network_node_id"):
                raise HTTPException(422, "Cada depósito precisa de store_id e network_node_id")
            try:
                if int(location.get("quantity", -1)) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(422, "A quantidade de cada depósito deve ser zero ou maior")
    listing = MarketplaceListing(
        tenant_id=user.tenant_id,
        marketplace_account_id=account.id,
        product_id=product.id,
        status="draft",
        price=payload.price,
        category_id=payload.category_id,
        family_name=payload.family_name,
        condition=payload.condition,
        currency_id=payload.currency_id.upper(),
        listing_type_id=payload.listing_type_id,
        available_quantity=payload.available_quantity,
        pictures_json=json.dumps(payload.pictures, ensure_ascii=False),
        attributes_json=json.dumps(payload.attributes, ensure_ascii=False),
        stock_locations_json=json.dumps(payload.stock_locations, ensure_ascii=False),
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
    if not connector.configured():
        raise HTTPException(409, "Marketplace ainda não está configurado com credenciais reais")

    base = local_listing(product)
    publish_options = {}
    if account.provider == "mercadolivre":
        token = _meli_access_token(session, account)
        pictures = [{"source": value} for value in json.loads(listing.pictures_json or "[]")]
        attributes = json.loads(listing.attributes_json or "[]")
        stock_locations = json.loads(listing.stock_locations_json or "[]")
        provided_attribute_ids = {attribute["id"] for attribute in attributes}
        try:
            category = connector.category(category_id=listing.category_id, access_token=token)
            settings_data = category.get("settings") or {}
            if not settings_data.get("listing_allowed"):
                raise HTTPException(422, "A categoria selecionada não permite publicações")
            if listing.condition not in (settings_data.get("item_conditions") or []):
                raise HTTPException(422, "A condição não é permitida para essa categoria")
            max_pictures = settings_data.get("max_pictures_per_item")
            if max_pictures and len(pictures) > max_pictures:
                raise HTTPException(422, f"A categoria aceita no máximo {max_pictures} imagens")

            category_attributes = connector.category_attributes(
                category_id=listing.category_id, access_token=token
            )
            required_ids = {
                attribute["id"] for attribute in category_attributes
                if (attribute.get("tags") or {}).get("required")
            }
            missing_ids = sorted(required_ids - provided_attribute_ids)
            if missing_ids:
                raise HTTPException(422, "Atributos obrigatórios ausentes: " + ", ".join(missing_ids))

            available_types = connector.available_listing_types(
                external_account_id=account.external_account_id,
                category_id=listing.category_id,
                access_token=token,
            )
            available_type_ids = {entry["id"] for entry in available_types}
            if listing.listing_type_id not in available_type_ids:
                raise HTTPException(422, "Tipo de anúncio indisponível para este seller e categoria")

            profile = connector.user_info(access_token=token)
            seller_tags = profile.get("tags") or []
            if "user_product_seller" not in seller_tags:
                raise HTTPException(
                    422,
                    "Este seller ainda não está habilitado pelo Mercado Livre para User Products.",
                )
            warehouse_management = "warehouse_management" in seller_tags
            if warehouse_management and not stock_locations:
                raise HTTPException(
                    422,
                    "Este seller usa estoque multi-origem; informe stock_locations dos depósitos.",
                )
            if not warehouse_management:
                stock_locations = []

            conditional_item = {
                "family_name": listing.family_name,
                "category_id": listing.category_id,
                "price": listing.price,
                "currency_id": listing.currency_id,
                "buying_mode": "buy_it_now",
                "listing_type_id": listing.listing_type_id,
                "condition": listing.condition,
                "pictures": pictures,
                "attributes": attributes,
            }
            if warehouse_management:
                conditional_item["stock_locations"] = stock_locations
            else:
                conditional_item["available_quantity"] = listing.available_quantity
            conditional = connector.conditional_required_attributes(
                category_id=listing.category_id,
                item=conditional_item,
                access_token=token,
            )
            conditional_ids = {attribute["id"] for attribute in conditional}
            missing_conditional = sorted(conditional_ids - provided_attribute_ids)
            if missing_conditional:
                raise HTTPException(
                    422,
                    "Atributos condicionais obrigatórios ausentes: " + ", ".join(missing_conditional),
                )
        except httpx.HTTPError as exc:
            message = _meli_http_error(exc)
            listing.publication_error = message
            session.commit()
            raise HTTPException(502, message) from exc

        publish_options = {
            "access_token": token,
            "category_id": listing.category_id,
            "family_name": listing.family_name,
            "condition": listing.condition,
            "currency_id": listing.currency_id,
            "listing_type_id": listing.listing_type_id,
            "available_quantity": listing.available_quantity,
            "pictures": pictures,
            "attributes": attributes,
            "stock_locations": stock_locations,
        }
    try:
        result = connector.publish(
            title=base["title"],
            description=base["description"],
            price=listing.price,
            external_account_id=account.external_account_id,
            **publish_options,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except httpx.HTTPError as exc:
        message = _meli_http_error(exc)
        listing.publication_error = message
        session.commit()
        raise HTTPException(502, message) from exc

    listing.external_listing_id = result.external_listing_id
    listing.user_product_id = result.user_product_id
    listing.status = result.status
    listing.publication_error = None
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

