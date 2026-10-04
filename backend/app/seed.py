from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Tenant, User, Supplier, Product, Offer, OfferHistory, TenantSupplier
from .core.config import get_settings
from .core.security import hash_password

settings = get_settings()

def seed(session: Session):
    if session.scalar(select(Tenant.id).limit(1)):
        return

    tenant = Tenant(name="DropJoy Demo", slug="joyce-demo")
    session.add(tenant)
    session.flush()

    session.add(User(
        tenant_id=tenant.id,
        name="Joyce",
        email=settings.demo_user_email.lower(),
        hashed_password=hash_password(settings.demo_user_password),
        role="owner",
        active=True,
    ))

    dropify = Supplier(name="Dropify", slug="dropify", integration_type="api", reliability=.92)
    dslite = Supplier(name="DSLite", slug="dslite", integration_type="api", reliability=.88)
    session.add_all([dropify, dslite])
    session.flush()

    session.add_all([
        TenantSupplier(tenant_id=tenant.id, supplier_id=dropify.id, enabled=True, mode="demo"),
        TenantSupplier(tenant_id=tenant.id, supplier_id=dslite.id, enabled=True, mode="demo"),
    ])

    products = [
        ("Cafeteira Elétrica 30 xícaras", "Eletroportáteis", 129.90, .90, [(dropify, 68.90, 82, 24), (dslite, 72.40, 118, 24)]),
        ("Kit Organizador Multiuso", "Casa", 54.90, .88, [(dropify, 26.90, 90, 24), (dslite, 24.50, 156, 24)]),
        ("Aspirador Portátil", "Casa", 84.90, .82, [(dropify, 41.90, 64, 24), (dslite, 43.20, 101, 48)]),
        ("Furadeira de Impacto", "Ferramentas", 179.90, .76, [(dropify, 116.90, 71, 24), (dslite, 109.00, 37, 48)]),
    ]

    now = datetime.now(timezone.utc)
    for idx, (name, category, sale, comp, offers) in enumerate(products, start=1):
        p = Product(external_key=f"demo-{idx}", name=name, category=category, sale_price=sale, competition_score=comp)
        session.add(p)
        session.flush()
        for supplier, cost, stock, hours in offers:
            o = Offer(
                product_id=p.id,
                supplier_id=supplier.id,
                supplier_sku=f"DEMO-{p.id}-{supplier.id}",
                cost=cost,
                stock=stock,
                shipping_hours=hours,
                updated_at=now,
            )
            session.add(o)
            session.flush()
            for days, delta, stock_delta in [(14, 3.2, -18), (7, 1.4, -8), (0, 0, 0)]:
                session.add(OfferHistory(
                    offer_id=o.id,
                    captured_at=now - timedelta(days=days),
                    cost=round(cost + delta, 2),
                    stock=max(0, stock + stock_delta),
                ))
    session.commit()
