import json

import httpx
import pytest

from city_simulator.domain.chat import ConsultantRequest
from city_simulator.domain.exceptions import ConsultantServiceError
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
