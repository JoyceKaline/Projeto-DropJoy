import httpx
from .base import SupplierItem
from ..core.config import get_settings

class DropifyConnector:
    """Adapter da Dropify.

    A Dropify publica que sua API JSON/REST cobre catálogo, preços, estoque,
    pedidos, frete, NF, etiquetas e webhooks. Os caminhos/autenticação reais
    devem vir da documentação/credenciais homologadas; por segurança este
    adapter NÃO inventa endpoints.
    """
    slug = "dropify"

    def __init__(self):
        self.settings = get_settings()

    def configured(self) -> bool:
        s = self.settings
        return bool(s.dropify_enabled and s.dropify_base_url and s.dropify_api_token and s.dropify_products_path)

    def list_items(self) -> list[SupplierItem]:
        if not self.configured():
            raise RuntimeError("Dropify não configurada. Preencha as variáveis de ambiente após obter credenciais homologadas.")

        s = self.settings
        url = s.dropify_base_url.rstrip("/") + "/" + s.dropify_products_path.lstrip("/")
        headers = {"Authorization": f"Bearer {s.dropify_api_token}", "Accept": "application/json"}
        response = httpx.get(url, headers=headers, timeout=30.0)
        response.raise_for_status()

        # O mapeamento de payload será implementado assim que a resposta real
        # da conta homologada estiver disponível. Evitamos supor o schema.
        raise NotImplementedError("Conexão HTTP pronta; falta mapear o schema real retornado pela conta Dropify homologada.")
