from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DropJoy API"
    app_version: str = "0.4.0"
    database_url: str = "sqlite:///./dropjoy.db"
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"
    marketplace_percent_fee: float = 0.20
    marketplace_fixed_fee: float = 4.00
    default_tenant_slug: str = "joyce-demo"

    # Dropify: preencher somente quando houver credenciais/documentação homologada.
    dropify_enabled: bool = False
    dropify_base_url: str | None = None
    dropify_api_token: str | None = None
    dropify_products_path: str | None = None
    dropify_stock_path: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
