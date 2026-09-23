import pytest
from pydantic import ValidationError

from city_simulator.core.config import Settings


def test_plain_postgresql_url_is_normalized_for_async_driver() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://user:password@localhost:5432/database",
    )
    assert settings.database_url == ("postgresql+asyncpg://user:password@localhost:5432/database")


def test_cors_origins_are_parsed_from_comma_separated_setting() -> None:
    settings = Settings(
        _env_file=None,
        cors_allowed_origins="https://frontend.example, http://localhost:5173,",
    )
    assert settings.allowed_origins == [
        "https://frontend.example",
        "http://localhost:5173",
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"app_debug": True},
        {"cors_allowed_origins": "*"},
        {"database_url": "sqlite+aiosqlite:///./production.db"},
    ],
)
def test_unsafe_production_configuration_is_rejected(overrides) -> None:
    values = {
        "app_env": "production",
        "database_url": "postgresql://user:password@localhost:5432/database",
        "cors_allowed_origins": "https://frontend.example",
        **overrides,
    }
    with pytest.raises(ValidationError, match="unsafe production configuration"):
        Settings(_env_file=None, **values)


def test_safe_production_configuration_is_accepted() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        app_debug=False,
        database_url="postgresql://user:password@localhost:5432/database",
        cors_allowed_origins="https://frontend.example",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://")
