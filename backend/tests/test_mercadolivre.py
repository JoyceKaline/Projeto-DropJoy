from app.marketplaces.mercadolivre import MercadoLivreMarketplaceConnector


class StubResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data

def test_mercadolivre_connector_starts_unconfigured():
    connector = MercadoLivreMarketplaceConnector()
    assert connector.provider == "mercadolivre"
    assert connector.api_base == "https://api.mercadolibre.com"
    assert connector.auth_base == "https://auth.mercadolivre.com.br/authorization"


def test_user_product_publish_uses_official_items_flow(monkeypatch):
    connector = MercadoLivreMarketplaceConnector()
    monkeypatch.setattr(connector.settings, "meli_enabled", True)
    monkeypatch.setattr(connector.settings, "meli_client_id", "app-id")
    monkeypatch.setattr(connector.settings, "meli_client_secret", "secret")
    monkeypatch.setattr(connector.settings, "meli_redirect_uri", "https://example.test/callback")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        if url.endswith("/items"):
            return StubResponse({"id": "MLB123", "status": "active", "user_product_id": "MLBU456"})
        return StubResponse({})

    monkeypatch.setattr("app.marketplaces.mercadolivre.httpx.post", fake_post)
    result = connector.publish(
        title="Título gerado não deve ir no payload UP",
        description="Descrição simples",
        price=129.9,
        external_account_id="42",
        access_token="token",
        category_id="MLB1234",
        family_name="Cafeteira Elétrica",
        condition="new",
        listing_type_id="gold_special",
        available_quantity=4,
        pictures=[{"source": "https://example.test/image.jpg"}],
        attributes=[{"id": "BRAND", "value_name": "DropJoy"}],
    )

    assert result.external_listing_id == "MLB123"
    assert result.user_product_id == "MLBU456"
    item_payload = calls[0][1]["json"]
    assert item_payload["family_name"] == "Cafeteira Elétrica"
    assert "title" not in item_payload
    assert item_payload["available_quantity"] == 4
    assert calls[1][0].endswith("/items/MLB123/description")
    assert calls[1][1]["json"] == {"plain_text": "Descrição simples"}


def test_publish_requires_user_product_fields(monkeypatch):
    connector = MercadoLivreMarketplaceConnector()
    monkeypatch.setattr(connector.settings, "meli_enabled", True)
    monkeypatch.setattr(connector.settings, "meli_client_id", "app-id")
    monkeypatch.setattr(connector.settings, "meli_client_secret", "secret")
    monkeypatch.setattr(connector.settings, "meli_redirect_uri", "https://example.test/callback")

    try:
        connector.publish(
            title="Produto",
            description="",
            price=10,
            external_account_id="42",
            access_token="token",
        )
        assert False, "Era esperado erro de validação"
    except ValueError as exc:
        assert "category_id" in str(exc)
        assert "pictures" in str(exc)


def test_multiwarehouse_publish_uses_stock_locations_endpoint(monkeypatch):
    connector = MercadoLivreMarketplaceConnector()
    monkeypatch.setattr(connector.settings, "meli_enabled", True)
    monkeypatch.setattr(connector.settings, "meli_client_id", "app-id")
    monkeypatch.setattr(connector.settings, "meli_client_secret", "secret")
    monkeypatch.setattr(connector.settings, "meli_redirect_uri", "https://example.test/callback")
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return StubResponse({"id": "MLB999", "status": "active", "user_product_id": "MLBU999"})

    monkeypatch.setattr("app.marketplaces.mercadolivre.httpx.post", fake_post)
    connector.publish(
        title="Produto",
        description="",
        price=10,
        external_account_id="42",
        access_token="token",
        category_id="MLB1234",
        family_name="Produto",
        condition="new",
        listing_type_id="gold_special",
        available_quantity=99,
        pictures=[{"source": "https://example.test/image.jpg"}],
        attributes=[{"id": "BRAND", "value_name": "DropJoy"}],
        stock_locations=[{"store_id": "1", "network_node_id": "BRSP1", "quantity": 3}],
    )

    assert calls[0][0].endswith("/items/multiwarehouse")
    assert "available_quantity" not in calls[0][1]["json"]
    assert calls[0][1]["json"]["stock_locations"][0]["quantity"] == 3

