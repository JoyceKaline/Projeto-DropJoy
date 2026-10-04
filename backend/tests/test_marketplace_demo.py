from app.marketplaces.demo import DemoMarketplaceConnector

def test_demo_marketplace_can_publish():
    connector = DemoMarketplaceConnector()
    assert connector.configured()
    result = connector.publish(title="Produto", description="Descrição", price=10.0, external_account_id="demo")
    assert result.status == "published"
    assert result.external_listing_id.startswith("DEMO-")
