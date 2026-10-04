from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import User
from ..core.auth import get_current_user
from ..core.security import verify_password, hash_password, create_access_token
from ..core.config import get_settings
from ..services.auth_tokens import issue_refresh_token, rotate_refresh_token, revoke_refresh_token, issue_password_reset, consume_password_reset, revoke_all_user_refresh_tokens
from ..services.audit import audit

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=200)

class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=500)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    new_password: str = Field(min_length=8, max_length=200)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: dict

def token_response(session: Session, user: User) -> dict:
    access = create_access_token(user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role)
    refresh = issue_refresh_token(session, user)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in_minutes": settings.access_token_minutes,
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "tenant_id": user.tenant_id},
    }

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)):
    user = session.scalar(select(User).where(User.email == payload.email.lower(), User.active.is_(True)))
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos")
    result = token_response(session, user)
    audit(session, tenant_id=user.tenant_id, user=user, action="auth.login")
    return result

@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, session: Session = Depends(get_db)):
    user = rotate_refresh_token(session, payload.refresh_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido ou expirado")
    return token_response(session, user)

@router.post("/logout")
def logout(payload: RefreshRequest, user: User = Depends(get_current_user), session: Session = Depends(get_db)):
    revoke_refresh_token(session, payload.refresh_token)
    audit(session, tenant_id=user.tenant_id, user=user, action="auth.logout")
    return {"status": "ok"}

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, session: Session = Depends(get_db)):
    user = session.scalar(select(User).where(User.email == payload.email.lower(), User.active.is_(True)))
    response = {"message": "Se o e-mail existir, uma instrução de recuperação será gerada."}
    if not user:
        return response
    token = issue_password_reset(session, user)
    audit(session, tenant_id=user.tenant_id, user=user, action="auth.password_reset_requested")
    if settings.environment.lower() in {"development", "test"} and settings.expose_reset_tokens_in_dev:
        response["development_reset_token"] = token
    return response

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, session: Session = Depends(get_db)):
    user = consume_password_reset(session, payload.token)
    if not user:
        raise HTTPException(status_code=400, detail="Token de recuperação inválido ou expirado")
    user.hashed_password = hash_password(payload.new_password)
    session.commit()
    revoke_all_user_refresh_tokens(session, user.id)
    audit(session, tenant_id=user.tenant_id, user=user, action="auth.password_reset_completed")
    return {"status": "ok"}

@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "tenant_id": user.tenant_id}
