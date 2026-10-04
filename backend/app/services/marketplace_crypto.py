import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken
from ..core.config import get_settings

settings = get_settings()

def _fernet() -> Fernet:
    if settings.marketplace_credential_key:
        key = settings.marketplace_credential_key.encode("utf-8")
    else:
        # Somente desenvolvimento/teste: chave determinística derivada do JWT secret.
        digest = hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)

def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")

def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("Não foi possível descriptografar a credencial do marketplace.") from exc
