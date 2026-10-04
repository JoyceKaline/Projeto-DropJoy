from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Tenant, Supplier, TenantSupplier
from app.services.tenant_scope import enabled_supplier_ids

def test_enabled_supplier_ids_are_tenant_scoped():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        t1=Tenant(name="A",slug="a",active=True); t2=Tenant(name="B",slug="b",active=True)
        sup=Supplier(name="S",slug="s",integration_type="demo",reliability=.9,active=True)
        s.add_all([t1,t2,sup]); s.flush()
        s.add_all([TenantSupplier(tenant_id=t1.id,supplier_id=sup.id,enabled=True,mode="demo"),TenantSupplier(tenant_id=t2.id,supplier_id=sup.id,enabled=False,mode="demo")]); s.commit()
        assert sup.id in enabled_supplier_ids(s,t1.id)
        assert sup.id not in enabled_supplier_ids(s,t2.id)
