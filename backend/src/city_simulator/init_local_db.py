"""Create missing tables for an explicitly selected local SQLite preview."""

import asyncio
import os
import sys

from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import create_async_engine

from city_simulator.infrastructure import models  # noqa: F401 - register ORM tables
from city_simulator.infrastructure.database import Base


async def initialize(database_url: URL) -> None:
    engine = create_async_engine(database_url.set(drivername="sqlite+aiosqlite"))
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()


def main() -> int:
    raw_url = os.environ.get("DATABASE_URL", "")
    try:
        database_url = make_url(raw_url)
    except ArgumentError:
        print("Set DATABASE_URL explicitly to a SQLite URL for local preview.", file=sys.stderr)
        return 2
    if database_url.get_backend_name() != "sqlite":
        print("DATABASE_URL must select SQLite; other databases are refused.", file=sys.stderr)
        return 2
    asyncio.run(initialize(database_url))
    print("Local SQLite preview tables are ready; existing data was preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
