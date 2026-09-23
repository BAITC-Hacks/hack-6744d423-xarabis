from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from city_simulator.infrastructure.database import get_db_session
from city_simulator.main import app, create_app

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


def test_readiness_returns_503_without_leaking_database_error() -> None:
    isolated_app = create_app()

    class UnavailableSession:
        async def execute(self, _statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("private connection details"))

    async def unavailable_session():
        yield UnavailableSession()

    isolated_app.dependency_overrides[get_db_session] = unavailable_session
    with TestClient(isolated_app) as isolated_client:
        response = isolated_client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "private connection details" not in response.text


def test_request_id_and_security_headers_are_added() -> None:
    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "frontend-request-42"},
    )
    assert response.headers["x-request-id"] == "frontend-request-42"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_oversized_request_is_rejected_before_json_parsing() -> None:
    response = client.post(
        "/api/v1/scenarios/validate",
        content=b"x" * 262_145,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_unexpected_error_is_sanitized() -> None:
    isolated_app = create_app()

    @isolated_app.get("/_test/error")
    async def raise_unexpected_error():
        raise RuntimeError("private database details")

    with TestClient(isolated_app, raise_server_exceptions=False) as isolated_client:
        response = isolated_client.get("/_test/error")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "private database details" not in response.text
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


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


def test_cors_exposes_diagnostic_headers_on_guard_errors() -> None:
    response = client.post(
        "/api/v1/scenarios/validate",
        content=b"x" * 262_145,
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:5173",
        },
    )
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    exposed = {
        item.strip().lower()
        for item in response.headers["access-control-expose-headers"].split(",")
    }
    assert {"x-request-id", "retry-after"} <= exposed


def test_catalog_endpoints() -> None:
    metadata = client.get("/api/v1/catalog").json()
    assert metadata["dataset_version"] == "1.0"
    assert metadata["budget"] == 100
    assert metadata["max_measures_per_direction"] == 2
    indicators = client.get("/api/v1/indicators").json()
    assert len(indicators) == 10
    assert indicators[0]["scale_description"] == "100 = нет пробок в час пик, 0 = стоит всё"
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


def test_too_many_decisions_is_reported_as_a_game_rule_violation() -> None:
    response = client.post(
        "/api/v1/scenarios/validate",
        json={
            "decisions": [
                {"measure_id": "M9", "district_id": "nura"},
                {"measure_id": "M11", "district_id": "nura"},
                {"measure_id": "M10", "district_id": "nura"},
                {"measure_id": "M12"},
                {"measure_id": "M4", "district_id": "saryarka"},
                {"measure_id": "M1", "district_id": "esil"},
            ]
        },
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "scenario_validation_error"
    assert [item["code"] for item in error["details"]] == ["too_many_decisions"]


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
    assert schema["info"]["version"] == "0.6.0"
    paths = schema["paths"]
    assert "get" in paths["/api/v1/scenarios"]
    assert "post" in paths["/api/v1/scenarios/{scenario_id}/reset"]
    assert "delete" in paths["/api/v1/scenarios/{scenario_id}"]
    assert "post" in paths["/api/v1/scenarios/{scenario_id}/chat/messages"]
    assert "409" in paths["/api/v1/scenarios/{scenario_id}/decisions"]["put"]["responses"]
