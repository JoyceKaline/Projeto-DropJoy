import httpx
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
        return bool(s.meli_client_id and s.meli_client_secret and s.meli_redirect_uri)

    def configured(self) -> bool:
        s = self.settings
        return bool(s.meli_enabled and self.app_configured() and s.meli_access_token and s.meli_user_id)

    def authorization_url(self, *, state: str, code_challenge: str | None = None) -> str:
        if not self.app_configured():
            raise RuntimeError("Aplicação Mercado Livre ainda não configurada.")
        params = {
            "response_type": "code",
            "client_id": self.settings.meli_client_id,
            "redirect_uri": self.settings.meli_redirect_uri,
            "state": state,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return self.auth_base + "?" + urlencode(params)

    def user_info(self) -> dict:
        if not self.configured():
            raise RuntimeError("Mercado Livre ainda não configurado com access token e user id.")
        response = httpx.get(
            self.api_base + "/users/me",
            headers={"Authorization": f"Bearer {self.settings.meli_access_token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def publish(self, *, title: str, description: str, price: float, external_account_id: str) -> PublishResult:
        if not self.configured():
            raise RuntimeError("Mercado Livre ainda não configurado com credenciais reais.")
        raise NotImplementedError(
            "A publicação real no Mercado Livre aguarda o fluxo User Products e o mapeamento "
            "de categoria, atributos obrigatórios, condição, imagens e estoque. "
            "O DropJoy não publica usando um contrato legado incompleto."
        )
