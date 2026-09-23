import pytest
from fastapi.testclient import TestClient

from city_simulator.main import app

client = TestClient(app)


def simulate(turns: list[list[str]]) -> dict:
    response = client.post("/api/v1/sandbox/simulate", json={"turns": turns})
    assert response.status_code == 200, response.text
    return response.json()


def test_sandbox_catalog_and_initial_city() -> None:
    response = client.get("/api/v1/sandbox/catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["city_name"] == "Новый Берег"
    assert catalog["starting_budget"] == 100
    assert catalog["quarterly_income"] == 12
    assert catalog["max_turns"] == 12
    assert catalog["critical_threshold"] == 40
    assert catalog["target_value"] == 65
    assert {item["id"] for item in catalog["improvements"]} == {
        "bus",
        "signals",
        "park",
        "filter",
        "school",
    }
    state = simulate([])
    assert state["city_name"] == catalog["city_name"]
    assert state["quarter"] == 1
    assert state["budget"] == 100
    assert state["score"] == 29.3
    assert {zone["id"]: zone["value"] for zone in state["zones"]} == {
        "transport": 28,
        "air": 34,
        "education": 26,
    }
    assert state["built"] == state["turns"] == state["last_changes"] == []
    assert state["last_income"] == 0
    assert state["status"] == "playing"


def test_full_game_replays_deterministically_and_resets_without_shared_state() -> None:
    first = simulate([["bus", "school", "park"]])
    assert first["budget"] == 40  # 100 - 22 - 32 - 18 + 12
    assert first["quarter"] == 2
    assert first["status"] == "playing"
    assert first["last_income"] == 12
    turns = [["bus", "school", "park"], ["signals"], ["filter"]]
    result = simulate(turns)
    assert result["quarter"] == 4
    assert result["budget"] == 22
    assert result["score"] == 74.7
    assert result["status"] == "won"
    assert {zone["id"]: zone["value"] for zone in result["zones"]} == {
        "transport": 70,
        "air": 86,
        "education": 68,
    }
    assert result["built"] == ["bus", "school", "park", "signals", "filter"]
    assert result["turns"] == turns
    assert result["last_changes"] == [{"zone_id": "air", "before": 56, "after": 86}]
    assert simulate(turns) == result
    assert simulate([])["budget"] == 100


def test_changes_aggregate_same_zone_and_empty_quarter_earns_income() -> None:
    result = simulate([["bus", "signals"]])
    assert result["last_changes"] == [{"zone_id": "transport", "before": 28, "after": 70}]
    result = simulate([["bus", "signals"], []])
    assert result["budget"] == 86
    assert result["last_changes"] == []
    assert result["last_income"] == 12


def test_twelve_turns_finish_without_claiming_victory() -> None:
    result = simulate([[] for _ in range(12)])
    assert result["quarter"] == 13
    assert result["budget"] == 244
    assert result["status"] == "finished"


@pytest.mark.parametrize(
    "payload",
    [
        {"turns": [["unknown"]]},
        {"turns": [["bus", "bus"]]},
        {"turns": [["bus"], ["bus"]]},
        # Only 40 remain: next quarter's income must not fund this 42-cost order.
        {"turns": [["bus", "school", "park"], ["signals", "filter"]]},
        {"turns": [[] for _ in range(13)]},
        {"turns": [["bus", "signals", "park", "school"]]},
        {"turns": "bus"},
        {"turns": [[1]]},
        {"turns": [], "budget": 999},
        {},
    ],
)
def test_invalid_sandbox_requests_are_rejected(payload: dict) -> None:
    response = client.post("/api/v1/sandbox/simulate", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"invalid_request", "sandbox_validation_error"}
