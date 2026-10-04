from app.marketplaces.mercadolivre import MercadoLivreMarketplaceConnector

def test_mercadolivre_connector_starts_unconfigured():
    connector = MercadoLivreMarketplaceConnector()
    assert connector.provider == "mercadolivre"
    assert connector.api_base == "https://api.mercadolibre.com"
    assert connector.auth_base == "https://auth.mercadolivre.com.br/authorization"
