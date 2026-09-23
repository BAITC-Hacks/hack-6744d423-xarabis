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
