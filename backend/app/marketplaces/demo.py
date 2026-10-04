from uuid import uuid4
from typing import Any
from .base import PublishResult

class DemoMarketplaceConnector:
    provider = "demo"
    def configured(self) -> bool:
        return True
    def publish(
        self,
        *,
        title: str,
        description: str,
        price: float,
        external_account_id: str,
        **kwargs: Any,
    ) -> PublishResult:
        return PublishResult(external_listing_id=f"DEMO-{uuid4().hex[:12].upper()}")

