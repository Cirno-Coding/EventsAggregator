from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Настройки приложения, читаемые из переменных окружения и файла .env.
    """

    app_name: str = Field(default="events-aggregator", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_connection_string: str | None = Field(default=None, alias="POSTGRES_CONNECTION_STRING")

    events_provider_base_url: str | None = Field(
        default=None,
        alias="EVENTS_PROVIDER_BASE_URL",
    )
    events_provider_api_key: str | None = Field(
        default=None,
        alias="EVENTS_PROVIDER_API_KEY",
    )

    enable_background_sync: bool = Field(default=False, alias="ENABLE_BACKGROUND_SYNC")
    sync_interval_seconds: int = Field(
        default=86400,  # 24 часа
        alias="SYNC_INTERVAL_SECONDS",
    )
    seats_cache_ttl_seconds: int = Field(
        default=30,  # 30 секунд
        alias="SEATS_CACHE_TTL_SECONDS",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    @property
    def database_url(self) -> str:
        """
        Вернуть URL БД в формате, подходящем для асинхронного драйвера asyncpg переменная `postgres_connection_string`.
        """
        raw_url = self.database_url_env or self.postgres_connection_string

        if raw_url is None:
            raise RuntimeError("Не задана переменная DATABASE_URL или POSTGRES_CONNECTION_STRING.")
        if raw_url.startswith("postgresql+asyncpg://"):
            return raw_url

        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)

        return raw_url


@lru_cache
def get_settings() -> Settings:
    """
    Создать и закэшировать настройки приложения.
    """
    return Settings()
