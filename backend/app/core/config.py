from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DropJoy API"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str = "sqlite:///./dropjoy.db"
    auto_create_schema: bool = True
    seed_demo_data: bool = True
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 30
    refresh_token_days: int = 14
    password_reset_minutes: int = 30
    expose_reset_tokens_in_dev: bool = True
    demo_user_email: str = "joyce@demo.local"
    demo_user_password: str = "dropjoy-demo"

    bootstrap_tenant_name: str | None = None
    bootstrap_tenant_slug: str | None = None
    bootstrap_owner_name: str | None = None
    bootstrap_owner_email: str | None = None
    bootstrap_owner_password: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    password_reset_base_url: str = "http://127.0.0.1:5500/?reset_token="

    openai_api_key: str | None = None
    openai_model: str = "gpt-6-luna"

    marketplace_percent_fee: float = 0.20
    marketplace_fixed_fee: float = 4.00

    dropify_enabled: bool = False
    dropify_base_url: str | None = None
    dropify_api_token: str | None = None
    dropify_products_path: str | None = None
    dropify_stock_path: str | None = None

    dslite_enabled: bool = False
    dslite_base_url: str | None = None
    dslite_api_token: str | None = None
    dslite_products_path: str | None = None

    shopee_enabled: bool = False
    shopee_base_url: str | None = None
    shopee_shop_id: str | None = None
    shopee_access_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from_email)

    def validate_runtime_security(self) -> None:
        if self.environment.lower() not in {"development", "test"} and self.jwt_secret_key == "dev-only-change-me":
            raise RuntimeError("JWT_SECRET_KEY precisa ser alterada fora do ambiente de desenvolvimento.")

@lru_cache
def get_settings() -> Settings:
    return Settings()
