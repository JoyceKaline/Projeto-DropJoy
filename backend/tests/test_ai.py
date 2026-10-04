from types import SimpleNamespace
from app.services.ai import local_listing

def test_local_listing_does_not_invent_specs():
    product = SimpleNamespace(name="Cafeteira Elétrica", category="Eletroportáteis", sale_price=99.90)
    result = local_listing(product)
    assert result["provider"] == "local"
    assert "Cafeteira" in result["title"]
    assert "Confirme especificações" in result["description"]
    assert len(result["keywords"]) > 0
