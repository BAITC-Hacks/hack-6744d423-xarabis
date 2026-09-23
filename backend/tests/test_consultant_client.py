import json

import httpx
import pytest

from city_simulator.domain.chat import ConsultantRequest
from city_simulator.domain.exceptions import ConsultantServiceError
from city_simulator.domain.services import ScoreCalculator
from city_simulator.infrastructure.consultant_client import HttpxConsultantGateway


@pytest.mark.asyncio
async def test_consultant_client_sends_exact_contract_and_validates_response() -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "answer": "Ответ",
                "strengths": [],
                "risks": [],
                "recommendations": [],
                "follow_up_question": None,
            },
        )

    async with httpx.AsyncClient(
        base_url="http://consultant.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        gateway = HttpxConsultantGateway(
            base_url="http://unused.test",
            timeout_seconds=1,
            client=client,
        )
        report = await gateway.generate(
            ConsultantRequest(
                message="Вопрос",
                history=(),
                selected_measures=(),
                budget_remaining=100,
                simulation_result=None,
            )
        )

    assert report.answer == "Ответ"
    assert captured == {
        "message": "Вопрос",
        "history": [],
        "context": {
            "selected_measures": [],
            "budget_remaining": 100,
            "simulation_result": None,
        },
    }


@pytest.mark.asyncio
async def test_consultant_client_maps_contract_drift_to_gateway_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"error": {"code": "invalid_request"}})

    async with httpx.AsyncClient(
        base_url="http://consultant.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        gateway = HttpxConsultantGateway(
            base_url="http://unused.test",
            timeout_seconds=1,
            client=client,
        )
        with pytest.raises(ConsultantServiceError, match="ai_contract_mismatch"):
            await gateway.generate(
                ConsultantRequest(
                    message="Вопрос",
                    history=(),
                    selected_measures=(),
                    budget_remaining=100,
                    simulation_result=None,
                )
            )


@pytest.mark.asyncio
async def test_consultant_client_sends_complete_calculated_result_contract(
    dataset,
    example_decisions,
) -> None:
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "answer": "Расчёт принят.",
                "strengths": [],
                "risks": [],
                "recommendations": [],
                "follow_up_question": None,
            },
        )

    result = ScoreCalculator().calculate(example_decisions, dataset)
    async with httpx.AsyncClient(
        base_url="http://consultant.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        gateway = HttpxConsultantGateway(
            base_url="http://unused.test",
            timeout_seconds=1,
            client=client,
        )
        await gateway.generate(
            ConsultantRequest(
                message="Объясни расчёт",
                history=(),
                selected_measures=example_decisions,
                budget_remaining=5,
                simulation_result=result,
            )
        )

    context = captured["context"]
    assert context["budget_remaining"] == 5
    assert context["selected_measures"] == [
        {"measure_id": "M7", "district_id": "nura"},
        {"measure_id": "M8", "district_id": "nura"},
        {"measure_id": "M10", "district_id": "nura"},
        {"measure_id": "M12", "district_id": None},
        {"measure_id": "M5", "district_id": "saryarka"},
    ]
    simulation = context["simulation_result"]
    assert set(simulation) == {
        "score_before",
        "score_after",
        "score_delta",
        "districts",
        "critical_before",
        "critical_after",
        "effects",
    }
    assert simulation["score_after"] == pytest.approx(56.54307)
    assert {item["district_id"] for item in simulation["districts"]} == {
        "esil",
        "almaty",
        "saryarka",
        "baikonur",
        "nura",
    }
    assert len(simulation["critical_before"]) == 2
    assert simulation["critical_after"] == []
    assert all(
        len(effect["measure_ids"]) == (2 if effect["kind"] == "synergy" else 1)
        for effect in simulation["effects"]
    )


@pytest.mark.asyncio
async def test_consultant_client_rejects_malformed_success_response() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"answer": "Нет обязательных блоков"})

    async with httpx.AsyncClient(
        base_url="http://consultant.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        gateway = HttpxConsultantGateway(
            base_url="http://unused.test",
            timeout_seconds=1,
            client=client,
        )
        with pytest.raises(ConsultantServiceError, match="invalid_ai_response"):
            await gateway.generate(
                ConsultantRequest(
                    message="Вопрос",
                    history=(),
                    selected_measures=(),
                    budget_remaining=100,
                    simulation_result=None,
                )
            )
