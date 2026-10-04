import httpx
from typing import Any
from urllib.parse import urlencode
from .base import PublishResult
from ..core.config import get_settings

class MercadoLivreMarketplaceConnector:
    provider = "mercadolivre"
    api_base = "https://api.mercadolibre.com"
    auth_base = "https://auth.mercadolivre.com.br/authorization"

    def __init__(self):
        self.settings = get_settings()

    def app_configured(self) -> bool:
        s = self.settings
        return bool(s.meli_enabled and s.meli_client_id and s.meli_client_secret and s.meli_redirect_uri)

    def configured(self) -> bool:
        # A aplicação pode estar pronta mesmo sem um seller conectado.
        return self.app_configured()

    def authorization_url(self, *, state: str, code_challenge: str) -> str:
        if not self.app_configured():
            raise RuntimeError("Aplicação Mercado Livre ainda não configurada.")
        params = {
            "response_type": "code",
            "client_id": self.settings.meli_client_id,
            "redirect_uri": self.settings.meli_redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return self.auth_base + "?" + urlencode(params)

    def exchange_code(self, *, code: str, code_verifier: str) -> dict:
        if not self.app_configured():
            raise RuntimeError("Aplicação Mercado Livre ainda não configurada.")
        response = httpx.post(
            self.api_base + "/oauth/token",
            headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "client_id": self.settings.meli_client_id,
                "client_secret": self.settings.meli_client_secret,
                "code": code,
                "redirect_uri": self.settings.meli_redirect_uri,
                "code_verifier": code_verifier,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def refresh_access_token(self, *, refresh_token: str) -> dict:
        if not self.app_configured():
            raise RuntimeError("Aplicação Mercado Livre ainda não configurada.")
        response = httpx.post(
            self.api_base + "/oauth/token",
            headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "client_id": self.settings.meli_client_id,
                "client_secret": self.settings.meli_client_secret,
                "refresh_token": refresh_token,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def user_info(self, *, access_token: str) -> dict:
        response = httpx.get(
            self.api_base + "/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _headers(access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def predict_categories(self, *, query: str, access_token: str, limit: int = 4) -> list[dict]:
        response = httpx.get(
            self.api_base + "/sites/MLB/domain_discovery/search",
            headers=self._headers(access_token),
            params={"q": query, "limit": limit},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def category(self, *, category_id: str, access_token: str) -> dict:
        response = httpx.get(
            self.api_base + f"/categories/{category_id}",
            headers=self._headers(access_token),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def category_attributes(self, *, category_id: str, access_token: str) -> list[dict]:
        response = httpx.get(
            self.api_base + f"/categories/{category_id}/attributes",
            headers=self._headers(access_token),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def available_listing_types(
        self, *, external_account_id: str, category_id: str, access_token: str
    ) -> list[dict]:
        response = httpx.get(
            self.api_base + f"/users/{external_account_id}/available_listing_types",
            headers=self._headers(access_token),
            params={"category_id": category_id},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("available", [])

    def stock_locations(self, *, external_account_id: str, access_token: str) -> list[dict]:
        response = httpx.get(
            self.api_base + f"/users/{external_account_id}/stores/search",
            headers=self._headers(access_token),
            params={"tags": "stock_location"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("results", [])

    def conditional_required_attributes(
        self, *, category_id: str, item: dict[str, Any], access_token: str
    ) -> list[dict]:
        response = httpx.post(
            self.api_base + f"/categories/{category_id}/attributes/conditional",
            headers={**self._headers(access_token), "Content-Type": "application/json"},
            json=item,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json().get("required_attributes", [])

    def publish(
        self,
        *,
        title: str,
        description: str,
        price: float,
        external_account_id: str,
        access_token: str | None = None,
        category_id: str | None = None,
        family_name: str | None = None,
        condition: str | None = None,
        currency_id: str = "BRL",
        listing_type_id: str | None = None,
        available_quantity: int | None = None,
        pictures: list[dict[str, str]] | None = None,
        attributes: list[dict[str, str]] | None = None,
        stock_locations: list[dict[str, Any]] | None = None,
        **_: Any,
    ) -> PublishResult:
        if not self.app_configured():
            raise RuntimeError("Mercado Livre ainda não configurado com credenciais da aplicação.")
        required = {
            "access_token": access_token,
            "category_id": category_id,
            "family_name": family_name,
            "condition": condition,
            "listing_type_id": listing_type_id,
            "pictures": pictures,
            "attributes": attributes,
        }
        missing = [key for key, value in required.items() if value is None or value == [] or value == ""]
        if missing:
            raise ValueError("Campos obrigatórios ausentes para o Mercado Livre: " + ", ".join(missing))

        item: dict[str, Any] = {
            "family_name": family_name,
            "category_id": category_id,
            "price": price,
            "currency_id": currency_id,
            "buying_mode": "buy_it_now",
            "listing_type_id": listing_type_id,
            "condition": condition,
            "pictures": pictures,
            "attributes": attributes,
        }
        path = "/items"
        if stock_locations:
            item["stock_locations"] = stock_locations
            path = "/items/multiwarehouse"
        elif available_quantity is not None:
            item["available_quantity"] = available_quantity
        else:
            raise ValueError("Informe available_quantity ou stock_locations")
        headers = {**self._headers(access_token), "Content-Type": "application/json"}
        response = httpx.post(
            self.api_base + path,
            headers=headers,
            json=item,
            timeout=30.0,
        )
        response.raise_for_status()
        created = response.json()
        item_id = str(created["id"])

        if description.strip():
            description_response = httpx.post(
                self.api_base + f"/items/{item_id}/description",
                headers=headers,
                json={"plain_text": description.strip()},
                timeout=30.0,
            )
            description_response.raise_for_status()

        return PublishResult(
            external_listing_id=item_id,
            status=str(created.get("status") or "published"),
            user_product_id=created.get("user_product_id"),
        )

