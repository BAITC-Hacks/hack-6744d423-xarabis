import pytest
from fastapi.testclient import TestClient

from city_simulator.main import app

client = TestClient(app)
URL = "/api/v1/sandbox/v2/simulate"


def choice(district: str, improvement: str) -> dict:
    return {"district_id": district, "improvement_id": improvement}


def simulate(turns: list[list[dict]]) -> dict:
    response = client.post(URL, json={"turns": turns})
    assert response.status_code == 200, response.text
    return response.json()


def test_catalog_and_initial_district_scores() -> None:
    response = client.get("/api/v1/sandbox/v2/catalog")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["rules_version"] == "districts-v2"
    assert catalog["starting_budget"] == 200
    assert catalog["quarterly_income"] == 25
    assert catalog["max_turns"] == 12
    assert catalog["critical_threshold"] == 40
    assert catalog["target_value"] == 65
    assert {item["id"] for item in catalog["improvements"]} == {
        "bus",
        "signals",
        "park",
        "filter",
        "school",
        "repair",
    }
    state = simulate([])
    assert state["rules_version"] == catalog["rules_version"]
    assert state["city_name"] == catalog["city_name"] == "Новый Берег"
    assert state["quarter"] == 1
    assert state["budget"] == 200
    assert state["score"] == 50.7
    assert [(d["id"], d["name"], d["score"]) for d in state["districts"]] == [
        ("esil", "Есиль", 65.3),
        ("almaty", "Алматы", 42.7),
        ("saryarka", "Сарыарка", 40.0),
        ("baikonur", "Байконур", 74.0),
        ("nura", "Нура", 31.3),
    ]
    assert all(d["description"] and d["built"] == [] for d in state["districts"])
    assert state["turns"] == state["last_changes"] == []
    assert state["last_income"] == 0
    assert state["status"] == "playing"


def test_build_affects_only_selected_district_and_can_repeat_elsewhere() -> None:
    initial = simulate([])
    turns = [[choice("almaty", "bus"), choice("nura", "bus")]]
    state = simulate(turns)
    assert state["districts"][1]["values"] == {"transport": 52, "air": 52, "education": 48}
    assert state["districts"][4]["values"] == {"transport": 50, "air": 42, "education": 26}
    assert state["districts"][1]["built"] == state["districts"][4]["built"] == ["bus"]
    for index in (0, 2, 3):
        assert state["districts"][index] == initial["districts"][index]
    assert state["budget"] == 181
    assert state["last_income"] == 25
    assert state["last_changes"] == [
        {"district_id": "almaty", "indicator_id": "transport", "before": 28, "after": 52},
        {"district_id": "nura", "indicator_id": "transport", "before": 26, "after": 50},
    ]
    assert simulate(turns) == state
    assert simulate([]) == initial


def test_changes_aggregate_per_district_and_indicator_with_cap() -> None:
    state = simulate([[choice("baikonur", "bus"), choice("baikonur", "repair")]])
    assert state["districts"][3]["values"]["transport"] == 100
    assert state["districts"][3]["built"] == ["bus", "repair"]
    assert state["last_changes"] == [
        {"district_id": "baikonur", "indicator_id": "transport", "before": 76, "after": 100}
    ]
    assert state["budget"] == 173


def test_empty_turn_earns_income_and_twelve_turns_finish() -> None:
    state = simulate([[]])
    assert state["budget"] == 225
    assert state["quarter"] == 2
    assert state["last_changes"] == []
    assert state["last_income"] == 25
    state = simulate([[] for _ in range(12)])
    assert state["budget"] == 500
    assert state["quarter"] == 13
    assert state["status"] == "finished"


def test_full_campaign_requires_every_indicator_in_every_district() -> None:
    turns = [
        [choice("esil", "school"), choice("almaty", "bus"), choice("almaty", "signals")],
        [choice("almaty", "park"), choice("almaty", "school"), choice("saryarka", "repair")],
        [choice("saryarka", "park"), choice("saryarka", "filter"), choice("saryarka", "school")],
        [choice("nura", "bus"), choice("nura", "signals")],
        [],
        [choice("nura", "filter"), choice("nura", "school")],
    ]
    previous = simulate(turns[:-1])
    assert previous["status"] == "playing"
    assert previous["score"] > 65
    state = simulate(turns)
    assert state["status"] == "won"
    assert state["quarter"] == 7
    assert state["budget"] == 28
    assert state["score"] == 76.4
    assert state["turns"] == turns
    assert all(value >= 65 for d in state["districts"] for value in d["values"].values())
    assert simulate(turns) == state


def test_income_cannot_fund_current_turn() -> None:
    turns = [
        [choice("esil", "school"), choice("almaty", "school"), choice("saryarka", "school")],
        [choice("nura", "school"), choice("baikonur", "school"), choice("baikonur", "repair")],
        [choice("esil", "repair"), choice("almaty", "repair")],
    ]
    assert simulate(turns)["budget"] == 25
    response = client.post(URL, json={"turns": [*turns, [choice("saryarka", "filter")]]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "sandbox_validation_error"


@pytest.mark.parametrize(
    "payload",
    [
        {"turns": [[choice("unknown", "bus")]]},
        {"turns": [[choice("esil", "unknown")]]},
        {"turns": [[choice("esil", "bus"), choice("esil", "bus")]]},
        {"turns": [[choice("esil", "bus")], [choice("esil", "bus")]]},
        {"turns": [[choice("esil", item) for item in ("bus", "repair", "school", "park")]]},
        {"turns": [[] for _ in range(13)]},
        {"turns": "bus"},
        {"turns": [["bus"]]},
        {"turns": [[{}]]},
        {"turns": [[{"district_id": 1, "improvement_id": "bus"}]]},
        {"turns": [[{**choice("esil", "bus"), "cost": 0}]]},
        {"turns": [[choice("e" * 33, "bus")]]},
        {"turns": [[choice("esil", "b" * 33)]]},
        {"turns": [], "budget": 999},
        {},
    ],
)
def test_invalid_history_rejected(payload: dict) -> None:
    response = client.post(URL, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"invalid_request", "sandbox_validation_error"}
