from datetime import timedelta
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from ..models import RefreshToken, PasswordResetToken, User
from ..core.config import get_settings
from ..core.security import new_opaque_token, hash_opaque_token, utcnow

settings = get_settings()

def issue_refresh_token(session: Session, user: User) -> str:
    raw = new_opaque_token()
    now = utcnow()
    session.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_opaque_token(raw),
        created_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    ))
    session.commit()
    return raw

def rotate_refresh_token(session: Session, raw_token: str) -> User | None:
    now = utcnow()
    token_hash = hash_opaque_token(raw_token)
    record = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not record or record.revoked_at is not None or record.expires_at <= now:
        return None
    user = session.get(User, record.user_id)
    if not user or not user.active:
        return None
    record.revoked_at = now
    session.commit()
    return user

def revoke_refresh_token(session: Session, raw_token: str) -> bool:
    token_hash = hash_opaque_token(raw_token)
    record = session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if not record:
        return False
    if record.revoked_at is None:
        record.revoked_at = utcnow()
        session.commit()
    return True

def revoke_all_user_refresh_tokens(session: Session, user_id: int) -> None:
    session.execute(update(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    ).values(revoked_at=utcnow()))
    session.commit()

def issue_password_reset(session: Session, user: User) -> str:
    raw = new_opaque_token()
    now = utcnow()
    session.add(PasswordResetToken(
        user_id=user.id,
        token_hash=hash_opaque_token(raw),
        created_at=now,
        expires_at=now + timedelta(minutes=settings.password_reset_minutes),
    ))
    session.commit()
    return raw

def consume_password_reset(session: Session, raw_token: str) -> User | None:
    now = utcnow()
    token_hash = hash_opaque_token(raw_token)
    record = session.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    if not record or record.used_at is not None or record.expires_at <= now:
        return None
    user = session.get(User, record.user_id)
    if not user or not user.active:
        return None
    record.used_at = now
    session.commit()
    return user
