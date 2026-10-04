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

    def publish(self, *, title: str, description: str, price: float, external_account_id: str) -> PublishResult:
        if not self.app_configured():
            raise RuntimeError("Mercado Livre ainda não configurado com credenciais da aplicação.")
        raise NotImplementedError(
            "A publicação real no Mercado Livre aguarda o fluxo User Products e o mapeamento "
            "de categoria, atributos obrigatórios, condição, imagens e estoque."
        )
