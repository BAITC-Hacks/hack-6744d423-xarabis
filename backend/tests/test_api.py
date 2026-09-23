from fastapi.testclient import TestClient

from city_simulator.main import app

client = TestClient(app)

EXAMPLE_REQUEST = {
    "decisions": [
        {"measure_id": "M7", "district_id": "nura"},
        {"measure_id": "M8", "district_id": "nura"},
        {"measure_id": "M10", "district_id": "nura"},
        {"measure_id": "M12"},
        {"measure_id": "M5", "district_id": "saryarka"},
    ]
}


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_allows_configured_frontend() -> None:
    response = client.options(
        "/api/v1/catalog",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_catalog_endpoints() -> None:
    metadata = client.get("/api/v1/catalog").json()
    assert metadata["dataset_version"] == "1.0"
    assert metadata["budget"] == 100
    assert len(client.get("/api/v1/indicators").json()) == 10
    districts = client.get("/api/v1/districts").json()
    assert len(districts) == 5
    assert districts[0]["id"] == "esil"
    assert len(client.get("/api/v1/measures").json()) == 14


def test_validate_partial_scenario() -> None:
    response = client.post(
        "/api/v1/scenarios/validate",
        json={"decisions": [{"measure_id": "M12"}]},
    )
    assert response.status_code == 200
    assert response.json() == {
        "valid": True,
        "decision_count": 1,
        "total_cost": 14,
        "remaining_budget": 86,
        "ready_for_calculation": False,
    }


def test_simulate_example_returns_ai_ready_trace() -> None:
    response = client.post("/api/v1/scenarios/simulate", json=EXAMPLE_REQUEST)

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_version"] == "1.0"
    assert body["formula_version"] == "1.0"
    assert body["total_cost"] == 95
    assert body["score_after"] == 56.54
    assert len(body["districts"]) == 5
    assert len(body["critical_before"]) == 2
    assert body["critical_after"] == []
    assert any(item["kind"] == "synergy" for item in body["effects"])
    assert "analysis" not in body


def test_invalid_scenario_returns_rule_details() -> None:
    response = client.post(
        "/api/v1/scenarios/simulate",
        json={"decisions": [{"measure_id": "M12"}]},
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "scenario_validation_error"
    assert error["details"] == [
        {
            "code": "decision_count_mismatch",
            "message": "Нужно выбрать ровно 5 мероприятий",
            "context": {"required": 5, "actual": 1},
        }
    ]


def test_unknown_request_fields_are_rejected() -> None:
    response = client.post(
        "/api/v1/scenarios/validate",
        json={"decisions": [], "simulation_result": {}},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_openapi_describes_frontend_integration_contract() -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == "0.5.0"
    paths = schema["paths"]
    assert "get" in paths["/api/v1/scenarios"]
    assert "post" in paths["/api/v1/scenarios/{scenario_id}/reset"]
    assert "delete" in paths["/api/v1/scenarios/{scenario_id}"]
    assert "post" in paths["/api/v1/scenarios/{scenario_id}/chat/messages"]
    assert "409" in paths["/api/v1/scenarios/{scenario_id}/decisions"]["put"]["responses"]
