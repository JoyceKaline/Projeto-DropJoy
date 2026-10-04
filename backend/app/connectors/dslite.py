import httpx
from .base import SupplierItem
from ..core.config import get_settings

class DSLiteConnector:
    slug = "dslite"

    def __init__(self):
        self.settings = get_settings()

    def configured(self) -> bool:
        s = self.settings
        return bool(s.dslite_enabled and s.dslite_base_url and s.dslite_api_token and s.dslite_products_path)

    def list_items(self) -> list[SupplierItem]:
        if not self.configured():
            raise RuntimeError("DSLite não configurada. Preencha as credenciais/documentação reais no ambiente.")
        s = self.settings
        url = s.dslite_base_url.rstrip("/") + "/" + s.dslite_products_path.lstrip("/")
        response = httpx.get(url, headers={"Authorization": f"Bearer {s.dslite_api_token}", "Accept": "application/json"}, timeout=30.0)
        response.raise_for_status()
        raise NotImplementedError("Conexão pronta; falta mapear o schema real retornado pela conta DSLite.")
