from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from .config import get_settings

settings = get_settings()
password_hash = PasswordHash.recommended()

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_access_token(*, user_id: int, tenant_id: int, email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise ValueError("Token inválido ou expirado") from exc

def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)

def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def utcnow() -> datetime:
    return datetime.now(timezone.utc)
