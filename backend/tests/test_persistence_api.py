import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from city_simulator.infrastructure.database import Base, get_db_session
from city_simulator.main import app

EXAMPLE_DECISIONS = [
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": None},
    {"measure_id": "M5", "district_id": "saryarka"},
]

ALTERNATIVE_DECISIONS = [
    {"measure_id": "M9", "district_id": "nura"},
    {"measure_id": "M11", "district_id": "esil"},
    {"measure_id": "M10", "district_id": "almaty"},
    {"measure_id": "M12", "district_id": None},
    {"measure_id": "M4", "district_id": "saryarka"},
]


@pytest.fixture
async def persistence_client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db_session, None)
    await engine.dispose()


def test_persisted_scenario_lifecycle(persistence_client: TestClient) -> None:
    assert persistence_client.get("/api/v1/ready").json() == {"status": "ready"}
    created_response = persistence_client.post("/api/v1/scenarios")
    assert created_response.status_code == 201
    created = created_response.json()
    scenario_id = created["id"]
    assert created["version"] == 1
    assert created["status"] == "draft"

    updated_response = persistence_client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 1, "decisions": EXAMPLE_DECISIONS},
    )
    assert updated_response.status_code == 200
    assert updated_response.json()["version"] == 2

    calculated_response = persistence_client.post(
        f"/api/v1/scenarios/{scenario_id}/calculate",
        json={"expected_version": 2},
    )
    assert calculated_response.status_code == 200
    calculation = calculated_response.json()
    assert calculation["scenario_version"] == 2
    assert calculation["simulation"]["score_after"] == 56.54

    scenario = persistence_client.get(f"/api/v1/scenarios/{scenario_id}").json()
    assert scenario["status"] == "calculated"

    current = persistence_client.get(f"/api/v1/scenarios/{scenario_id}/result")
    assert current.status_code == 200
    assert current.json()["id"] == calculation["id"]

    history = persistence_client.get(f"/api/v1/scenarios/{scenario_id}/results")
    assert history.status_code == 200
    assert len(history.json()) == 1

    changed = persistence_client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 2, "decisions": ALTERNATIVE_DECISIONS},
    )
    assert changed.status_code == 200
    assert changed.json()["version"] == 3
    assert changed.json()["status"] == "draft"

    no_current_result = persistence_client.get(f"/api/v1/scenarios/{scenario_id}/result")
    assert no_current_result.status_code == 404
    assert no_current_result.json()["error"]["code"] == "result_not_found"

    preserved_history = persistence_client.get(f"/api/v1/scenarios/{scenario_id}/results")
    assert len(preserved_history.json()) == 1


def test_stale_update_returns_conflict(persistence_client: TestClient) -> None:
    scenario = persistence_client.post("/api/v1/scenarios").json()
    scenario_id = scenario["id"]
    first = persistence_client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 1, "decisions": []},
    )
    assert first.status_code == 200

    stale = persistence_client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 1, "decisions": []},
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "scenario_version_conflict"


def test_missing_scenario_returns_not_found(persistence_client: TestClient) -> None:
    response = persistence_client.get("/api/v1/scenarios/00000000-0000-0000-0000-000000000001")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "scenario_not_found"
