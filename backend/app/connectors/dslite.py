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

    @staticmethod
    def _positive_price(product: dict) -> float:
        for field in ("preco_dropshipping", "preco_crossdocking", "preco_normal"):
            try:
                value = float(product.get(field) or 0)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return round(value, 2)
        raise ValueError("produto sem preço de custo válido")

    @classmethod
    def _map_product(cls, product: dict, default_supplier_id: object = None) -> SupplierItem:
        product_id = str(product.get("produtoid") or "").strip()
        title = str(product.get("titulo") or "").strip()
        if not product_id or not title:
            raise ValueError("produto sem produtoid ou titulo")

        supplier_id = product.get("fornecedorid") or default_supplier_id
        sku = str(product.get("produtoid_empresa") or product_id).strip()
        category = str(product.get("categoria_nome") or "Geral").strip() or "Geral"
        try:
            stock = max(0, int(float(product.get("estoque") or 0)))
        except (TypeError, ValueError):
            stock = 0

        return SupplierItem(
            external_key=f"dslite:{supplier_id}:{product_id}",
            sku=sku,
            name=title,
            category=category,
            cost=cls._positive_price(product),
            stock=stock,
            shipping_hours=24,
        )

    def list_items(self) -> list[SupplierItem]:
        if not self.configured():
            raise RuntimeError("DSLite não configurada. Preencha as credenciais/documentação reais no ambiente.")
        s = self.settings
        url = s.dslite_base_url.rstrip("/") + "/" + s.dslite_products_path.lstrip("/")
        headers = {"Token": s.dslite_api_token, "Accept": "application/json"}
        items: list[SupplierItem] = []
        page = 1
        records_seen = 0

        while page <= s.dslite_max_pages:
            response = httpx.get(
                url,
                headers=headers,
                params={"limit": s.dslite_page_size, "page": page},
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("produtos"), list):
                raise RuntimeError("Resposta DSLite inválida: campo 'produtos' ausente.")

            supplier_id = payload.get("fornecedorid")
            for product in payload["produtos"]:
                if not isinstance(product, dict):
                    continue
                try:
                    items.append(self._map_product(product, supplier_id))
                except ValueError:
                    continue

            details = payload.get("detalhesConsulta") or {}
            returned = int(details.get("registrosRetornados") or len(payload["produtos"]))
            total = int(details.get("totalRegistros") or len(items))
            records_seen += returned
            if returned == 0 or records_seen >= total:
                break
            page += 1

        return items
