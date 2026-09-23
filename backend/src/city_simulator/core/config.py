from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Akim for 5 Hours API"
    app_env: str = "local"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./xarabis.db"
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ai_service_url: str = "http://127.0.0.1:8001"
    ai_service_timeout_seconds: float = Field(default=45.0, gt=0, le=120)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
