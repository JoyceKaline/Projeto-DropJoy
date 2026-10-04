import sys
from sqlalchemy import select
from .db import SessionLocal
from .models import Tenant, User
from .core.config import get_settings
from .core.security import hash_password

settings = get_settings()

def bootstrap() -> int:
    required = {
        "BOOTSTRAP_TENANT_NAME": settings.bootstrap_tenant_name,
        "BOOTSTRAP_TENANT_SLUG": settings.bootstrap_tenant_slug,
        "BOOTSTRAP_OWNER_NAME": settings.bootstrap_owner_name,
        "BOOTSTRAP_OWNER_EMAIL": settings.bootstrap_owner_email,
        "BOOTSTRAP_OWNER_PASSWORD": settings.bootstrap_owner_password,
    }
    missing = [k for k,v in required.items() if not v]
    if missing:
        print("Bootstrap ignorado. Variáveis ausentes: " + ", ".join(missing))
        return 0
    if len(settings.bootstrap_owner_password or "") < 12:
        print("BOOTSTRAP_OWNER_PASSWORD deve ter pelo menos 12 caracteres em produção.")
        return 2
    with SessionLocal() as session:
        tenant = session.scalar(select(Tenant).where(Tenant.slug == settings.bootstrap_tenant_slug))
        if not tenant:
            tenant = Tenant(name=settings.bootstrap_tenant_name, slug=settings.bootstrap_tenant_slug, active=True)
            session.add(tenant); session.flush()
        email = settings.bootstrap_owner_email.lower()
        user = session.scalar(select(User).where(User.email == email))
        if not user:
            user = User(tenant_id=tenant.id, name=settings.bootstrap_owner_name, email=email, hashed_password=hash_password(settings.bootstrap_owner_password), role="owner", active=True)
            session.add(user)
        session.commit()
        print(f"Bootstrap concluído para tenant={tenant.slug}, owner={email}")
    return 0

def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "bootstrap":
        return bootstrap()
    print("Uso: python -m app.cli bootstrap")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
