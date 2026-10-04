import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import MarketplaceAccount, Tenant
from app.routers.marketplaces import _meli_account


def test_meli_account_lookup_is_tenant_scoped():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        first = Tenant(name="Primeiro", slug="primeiro", active=True)
        second = Tenant(name="Segundo", slug="segundo", active=True)
        session.add_all([first, second])
        session.flush()
        account = MarketplaceAccount(
            tenant_id=first.id,
            provider="mercadolivre",
            external_account_id="123",
            display_name="ML",
            status="connected",
        )
        session.add(account)
        session.commit()

        assert _meli_account(session, account_id=account.id, tenant_id=first.id).id == account.id
        with pytest.raises(HTTPException) as caught:
            _meli_account(session, account_id=account.id, tenant_id=second.id)
        assert caught.value.status_code == 404

