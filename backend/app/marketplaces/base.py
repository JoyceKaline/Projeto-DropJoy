from dataclasses import dataclass
from typing import Protocol

@dataclass
class PublishResult:
    external_listing_id: str
    status: str = "published"

class MarketplaceConnector(Protocol):
    provider: str
    def configured(self) -> bool: ...
    def publish(self, *, title: str, description: str, price: float, external_account_id: str) -> PublishResult: ...
