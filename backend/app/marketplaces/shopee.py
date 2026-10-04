from .base import PublishResult
from ..core.config import get_settings

class ShopeeMarketplaceConnector:
    provider = "shopee"
    def __init__(self):
        self.settings = get_settings()
    def configured(self) -> bool:
        s = self.settings
        return bool(s.shopee_enabled and s.shopee_base_url and s.shopee_shop_id and s.shopee_access_token)
    def publish(self, *, title: str, description: str, price: float, external_account_id: str) -> PublishResult:
        if not self.configured():
            raise RuntimeError("Shopee ainda não configurada com credenciais reais.")
        raise NotImplementedError("Publicação Shopee aguarda o contrato/autenticação oficial da conta. O DropJoy não inventa endpoints nem assinatura.")
