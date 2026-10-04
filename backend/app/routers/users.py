from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..core.auth import require_roles, get_current_user
from ..core.security import hash_password
from ..services.auth_tokens import revoke_all_user_refresh_tokens
from ..services.audit import audit

router = APIRouter(prefix="/api/users", tags=["users"])

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    role: str = "member"

class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = None
    active: bool | None = None

VALID_ROLES = {"owner", "admin", "member"}

def serialize(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "active": user.active, "tenant_id": user.tenant_id}

@router.get("")
def list_users(admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db)):
    users = session.scalars(select(User).where(User.tenant_id == admin.tenant_id).order_by(User.name)).all()
    return [serialize(x) for x in users]

@router.post("", status_code=201)
def create_user(payload: UserCreate, admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db)):
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, "Papel inválido")
    if payload.role == "owner" and admin.role != "owner":
        raise HTTPException(403, "Apenas owner pode criar outro owner")
    if session.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "E-mail já cadastrado")
    user = User(tenant_id=admin.tenant_id, name=payload.name.strip(), email=payload.email.lower(), hashed_password=hash_password(payload.password), role=payload.role, active=True)
    session.add(user); session.commit(); session.refresh(user)
    audit(session, tenant_id=admin.tenant_id, user=admin, action="user.created", entity_type="user", entity_id=user.id, details={"role": user.role})
    return serialize(user)

@router.patch("/{user_id}")
def patch_user(user_id: int, payload: UserPatch, admin: User = Depends(require_roles("owner", "admin")), session: Session = Depends(get_db)):
    user = session.scalar(select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id))
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    if user.role == "owner" and admin.role != "owner":
        raise HTTPException(403, "Apenas owner pode alterar owner")
    if payload.role is not None:
        if payload.role not in VALID_ROLES:
            raise HTTPException(400, "Papel inválido")
        if payload.role == "owner" and admin.role != "owner":
            raise HTTPException(403, "Apenas owner pode promover para owner")
        user.role = payload.role
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.active is not None:
        if user.id == admin.id and not payload.active:
            raise HTTPException(400, "Você não pode desativar a própria conta")
        user.active = payload.active
        if not user.active:
            revoke_all_user_refresh_tokens(session, user.id)
    session.commit()
    audit(session, tenant_id=admin.tenant_id, user=admin, action="user.updated", entity_type="user", entity_id=user.id)
    return serialize(user)
