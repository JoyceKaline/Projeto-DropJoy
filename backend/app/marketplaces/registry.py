from .demo import DemoMarketplaceConnector
from .shopee import ShopeeMarketplaceConnector

MARKETPLACES = {"demo": DemoMarketplaceConnector, "shopee": ShopeeMarketplaceConnector}

def marketplace_for(provider: str):
    klass = MARKETPLACES.get(provider)
    return klass() if klass else None
