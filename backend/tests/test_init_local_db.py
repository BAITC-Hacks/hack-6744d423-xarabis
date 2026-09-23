import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


def run_initializer(database_url: str | None) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("DATABASE_URL", None)
    if database_url is not None:
        environment["DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, "-m", "city_simulator.init_local_db"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_local_initializer_creates_tables_and_preserves_existing_data(tmp_path: Path) -> None:
    database_path = tmp_path / "preview.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    first = run_initializer(database_url)
    assert first.returncode == 0, first.stderr
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"scenarios", "scenario_decisions", "simulation_results"} <= tables
        connection.execute(
            "INSERT INTO scenarios (id, status, version, budget_limit) VALUES (?, ?, ?, ?)",
            ("0123456789abcdef0123456789abcdef", "draft", 1, 100),
        )
    second = run_initializer(database_url)
    assert second.returncode == 0, second.stderr
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT budget_limit FROM scenarios").fetchall() == [(100,)]


@pytest.mark.parametrize("database_url", [None, "postgresql://invalid:invalid@127.0.0.1:1/db"])
def test_local_initializer_requires_explicit_sqlite_without_connecting(
    database_url: str | None,
) -> None:
    result = run_initializer(database_url)
    assert result.returncode == 2
    assert "DATABASE_URL" in result.stderr
    assert "SQLite" in result.stderr
    assert "Traceback" not in result.stderr
