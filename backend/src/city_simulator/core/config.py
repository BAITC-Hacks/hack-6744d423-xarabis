import os
from dataclasses import dataclass
from functools import lru_cache


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    app_env: str
    debug: bool
    api_v1_prefix: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Akim for 5 Hours API"),
        app_env=os.getenv("APP_ENV", "local"),
        debug=_as_bool(os.getenv("APP_DEBUG", "false")),
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
    )
