"""All configuration from env (D-006). No provider-specific assumptions."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.webhook_guard import validate_secret_config


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["dev", "staging", "prod"] = "dev"
    log_level: str = "INFO"
    database_url: str  # runtime role with least privilege
    migration_database_url: str | None = None  # used only by Alembic/admin migration job
    redis_url: str = "redis://redis:6379/0"
    telegram_bot_token: SecretStr
    telegram_webhook_secret: SecretStr
    public_base_url: str
    key_provider: Literal["local"] = "local"
    master_key_file: str = "/run/secrets/master_key"
    sentry_dsn: SecretStr | None = None

    module_mailboxes_enabled: bool = False
    module_social_enabled: bool = False
    module_incidents_enabled: bool = False

    rate_limit_per_minute: int = Field(default=20, ge=1)

    @field_validator("telegram_webhook_secret")
    @classmethod
    def _secret_strong(cls, v: SecretStr) -> SecretStr:
        validate_secret_config(v.get_secret_value())
        return v

    @property
    def is_prod(self) -> bool:
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()
