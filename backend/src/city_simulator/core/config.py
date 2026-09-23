from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    max_request_body_bytes: int = Field(default=262_144, ge=1024, le=10_485_760)
    ai_chat_requests_per_minute: int = Field(default=10, ge=1, le=600)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.app_env.lower() not in {"production", "prod"}:
            return self
        violations: list[str] = []
        if self.app_debug:
            violations.append("APP_DEBUG must be false")
        if "*" in self.allowed_origins:
            violations.append("CORS_ALLOWED_ORIGINS must not contain '*'")
        if self.database_url.startswith("sqlite"):
            violations.append("DATABASE_URL must use PostgreSQL")
        if violations:
            raise ValueError("unsafe production configuration: " + "; ".join(violations))
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
