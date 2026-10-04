from .base import SupplierItem

class DemoConnector:
    slug = "demo"
    def configured(self) -> bool:
        return True
    def list_items(self) -> list[SupplierItem]:
        return []
