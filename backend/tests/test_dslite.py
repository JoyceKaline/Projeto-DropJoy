from types import SimpleNamespace

from app.connectors.dslite import DSLiteConnector


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _connector():
    connector = DSLiteConnector()
    connector.settings = SimpleNamespace(
        dslite_enabled=True,
        dslite_base_url="https://api.dslite.com.br/v1/",
        dslite_api_token="segredo-de-teste",
        dslite_products_path="CrossDocking/Catalogo/2",
        dslite_page_size=100,
        dslite_max_pages=10,
    )
    return connector


def test_dslite_maps_official_catalog_schema_and_token_header(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse({
            "fornecedorid": 2,
            "detalhesConsulta": {"registrosRetornados": 2, "totalRegistros": 2},
            "produtos": [
                {
                    "produtoid": "10408",
                    "produtoid_empresa": "SKU-CLIENTE",
                    "fornecedorid": 2,
                    "titulo": "Produto com preço drop",
                    "categoria_nome": "Casa / Cozinha",
                    "preco_dropshipping": 25.5,
                    "preco_crossdocking": 22,
                    "preco_normal": 20,
                    "estoque": 7,
                },
                {
                    "produtoid": "10409",
                    "produtoid_empresa": "",
                    "fornecedorid": 2,
                    "titulo": "Produto com fallback",
                    "categoria_nome": "Geral",
                    "preco_dropshipping": 0,
                    "preco_crossdocking": 19.9,
                    "preco_normal": 18,
                    "estoque": "3",
                },
            ],
        })

    monkeypatch.setattr("app.connectors.dslite.httpx.get", fake_get)
    items = _connector().list_items()

    assert len(items) == 2
    assert items[0].external_key == "dslite:2:10408"
    assert items[0].sku == "SKU-CLIENTE"
    assert items[0].cost == 25.5
    assert items[1].sku == "10409"
    assert items[1].cost == 19.9
    assert calls[0][0] == "https://api.dslite.com.br/v1/CrossDocking/Catalogo/2"
    assert calls[0][1]["headers"] == {"Token": "segredo-de-teste", "Accept": "application/json"}
    assert calls[0][1]["params"] == {"limit": 100, "page": 1}


def test_dslite_paginates_using_official_details(monkeypatch):
    pages = []

    def fake_get(_url, **kwargs):
        page = kwargs["params"]["page"]
        pages.append(page)
        product_id = str(100 + page)
        return FakeResponse({
            "fornecedorid": 2,
            "detalhesConsulta": {"registrosRetornados": 1, "totalRegistros": 2},
            "produtos": [{
                "produtoid": product_id,
                "titulo": f"Produto {page}",
                "preco_normal": 10,
                "estoque": 1,
            }],
        })

    monkeypatch.setattr("app.connectors.dslite.httpx.get", fake_get)
    items = _connector().list_items()

    assert pages == [1, 2]
    assert [item.external_key for item in items] == ["dslite:2:101", "dslite:2:102"]


def test_dslite_rejects_unexpected_schema(monkeypatch):
    monkeypatch.setattr("app.connectors.dslite.httpx.get", lambda *_args, **_kwargs: FakeResponse({"items": []}))
    try:
        _connector().list_items()
    except RuntimeError as exc:
        assert "produtos" in str(exc)
    else:
        raise AssertionError("Era esperado RuntimeError")
