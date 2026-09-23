from fastapi.testclient import TestClient

from city_simulator.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_catalogs() -> None:
    assert len(client.get("/api/v1/districts").json()) == 5
    assert len(client.get("/api/v1/measures").json()) == 14


def test_simulate_example() -> None:
    response = client.post(
        "/api/v1/scenarios/simulate",
        json={
            "decisions": [
                {"measure_id": "M7", "district_id": "nura"},
                {"measure_id": "M8", "district_id": "nura"},
                {"measure_id": "M10", "district_id": "nura"},
                {"measure_id": "M12"},
                {"measure_id": "M5", "district_id": "saryarka"},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_cost"] == 95
    assert body["score_after"] == 56.54
    assert body["critical_indicators_count"] == 0


def test_invalid_scenario_returns_rule_details() -> None:
    response = client.post(
        "/api/v1/scenarios/simulate",
        json={"decisions": [{"measure_id": "M12"}]},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "scenario_validation_error"
