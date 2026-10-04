from .demo import DemoMarketplaceConnector
from .shopee import ShopeeMarketplaceConnector
from .mercadolivre import MercadoLivreMarketplaceConnector

MARKETPLACES = {
    "demo": DemoMarketplaceConnector,
    "shopee": ShopeeMarketplaceConnector,
    "mercadolivre": MercadoLivreMarketplaceConnector,
}

def marketplace_for(provider: str):
    klass = MARKETPLACES.get(provider)
    return klass() if klass else None
