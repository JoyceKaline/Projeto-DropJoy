import base64
import hashlib
import secrets
from datetime import timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import MarketplaceOAuthCredential, MarketplaceOAuthSession
from ..core.security import utcnow
from .marketplace_crypto import encrypt_secret, decrypt_secret

def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def generate_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge

def create_oauth_session(session: Session, *, account_id: int, tenant_id: int, user_id: int, provider: str) -> tuple[str, str]:
    state = secrets.token_urlsafe(40)
    verifier, challenge = generate_pkce_pair()
    now = utcnow()
    session.add(MarketplaceOAuthSession(
        marketplace_account_id=account_id,
        tenant_id=tenant_id,
        user_id=user_id,
        provider=provider,
        state_hash=hashlib.sha256(state.encode("utf-8")).hexdigest(),
        code_verifier_encrypted=encrypt_secret(verifier),
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    ))
    session.commit()
    return state, challenge

def consume_oauth_session(session: Session, *, state: str, provider: str) -> tuple[MarketplaceOAuthSession, str] | None:
    state_hash = hashlib.sha256(state.encode("utf-8")).hexdigest()
    record = session.scalar(select(MarketplaceOAuthSession).where(
        MarketplaceOAuthSession.state_hash == state_hash,
        MarketplaceOAuthSession.provider == provider,
    ))
    if not record or record.used_at is not None or _aware(record.expires_at) <= utcnow():
        return None
    return record, decrypt_secret(record.code_verifier_encrypted)

def mark_oauth_session_used(session: Session, record: MarketplaceOAuthSession) -> None:
    record.used_at = utcnow()
    session.commit()

def upsert_oauth_credential(session: Session, *, account_id: int, token_data: dict) -> MarketplaceOAuthCredential:
    now = utcnow()
    expires_in = int(token_data.get("expires_in") or 21600)
    credential = session.scalar(select(MarketplaceOAuthCredential).where(
        MarketplaceOAuthCredential.marketplace_account_id == account_id
    ))
    if not credential:
        credential = MarketplaceOAuthCredential(marketplace_account_id=account_id)
        session.add(credential)
    credential.access_token_encrypted = encrypt_secret(token_data["access_token"])
    refresh = token_data.get("refresh_token")
    if refresh:
        credential.refresh_token_encrypted = encrypt_secret(refresh)
    credential.token_type = str(token_data.get("token_type") or "bearer")
    credential.scope = token_data.get("scope")
    credential.external_user_id = str(token_data["user_id"])
    credential.expires_at = now + timedelta(seconds=expires_in)
    credential.updated_at = now
    session.commit()
    session.refresh(credential)
    return credential

def credential_for_account(session: Session, account_id: int) -> MarketplaceOAuthCredential | None:
    return session.scalar(select(MarketplaceOAuthCredential).where(
        MarketplaceOAuthCredential.marketplace_account_id == account_id
    ))

def credential_status(credential: MarketplaceOAuthCredential | None) -> dict:
    if not credential:
        return {"connected": False, "expires_at": None, "expired": None}
    expires_at = _aware(credential.expires_at)
    return {
        "connected": True,
        "expires_at": expires_at.isoformat(),
        "expired": expires_at <= utcnow(),
        "external_user_id": credential.external_user_id,
    }

def access_token(credential: MarketplaceOAuthCredential) -> str:
    return decrypt_secret(credential.access_token_encrypted)

def refresh_token(credential: MarketplaceOAuthCredential) -> str | None:
    if not credential.refresh_token_encrypted:
        return None
    return decrypt_secret(credential.refresh_token_encrypted)
