from collections.abc import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User, Tenant
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticação necessária")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        tenant_id = int(payload["tenant_id"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado")

    user = session.scalar(select(User).where(User.id == user_id, User.tenant_id == tenant_id, User.active.is_(True)))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inválido ou inativo")
    tenant = session.scalar(select(Tenant).where(Tenant.id == user.tenant_id, Tenant.active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa")
    return user

def get_current_tenant(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Tenant:
    tenant = session.scalar(select(Tenant).where(Tenant.id == user.tenant_id, Tenant.active.is_(True)))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa")
    return tenant

def require_roles(*allowed: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")
        return user
    return dependency
