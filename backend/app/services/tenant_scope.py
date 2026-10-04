from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import TenantSupplier

def enabled_supplier_ids(session: Session, tenant_id: int) -> set[int]:
    return set(session.scalars(select(TenantSupplier.supplier_id).where(TenantSupplier.tenant_id == tenant_id, TenantSupplier.enabled.is_(True))).all())
