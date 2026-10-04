from dataclasses import dataclass
from typing import Protocol

@dataclass
class SupplierItem:
    external_key: str
    sku: str
    name: str
    category: str
    cost: float
    stock: int
    shipping_hours: int = 24

class SupplierConnector(Protocol):
    slug: str
    def configured(self) -> bool: ...
    def list_items(self) -> list[SupplierItem]: ...
