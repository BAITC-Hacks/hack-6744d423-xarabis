from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from city_simulator.domain.chat import (
    AnalysisBlock,
    ConsultantReport,
    ConsultantRequest,
)
from city_simulator.domain.chat_ports import ConsultantGateway
from city_simulator.domain.exceptions import ConsultantServiceError

KNOWN_AI_ERRORS = {
    "ai_not_configured",
    "ai_unavailable",
    "ai_timeout",
    "invalid_ai_response",
    "ai_refusal",
}


class _ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class _BlockPayload(_ContractModel):
    title: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=1200)


class _ReportPayload(_ContractModel):
    answer: str = Field(min_length=1, max_length=6000)
    strengths: list[_BlockPayload] = Field(max_length=5)
    risks: list[_BlockPayload] = Field(max_length=5)
    recommendations: list[_BlockPayload] = Field(max_length=5)
    follow_up_question: str | None = Field(min_length=1, max_length=500)


class HttpxConsultantGateway(ConsultantGateway):
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
        )

    async def generate(self, request: ConsultantRequest) -> ConsultantReport:
        try:
            response = await self._client.post("/chat", json=self._to_payload(request))
        except httpx.TimeoutException as exc:
            raise ConsultantServiceError("ai_timeout") from exc
        except httpx.HTTPError as exc:
            raise ConsultantServiceError("ai_unavailable") from exc

        if response.status_code != 200:
            raise ConsultantServiceError(self._error_code(response))
        try:
            payload = _ReportPayload.model_validate_json(response.content)
        except (ValidationError, ValueError) as exc:
            raise ConsultantServiceError("invalid_ai_response") from exc
        return ConsultantReport(
            answer=payload.answer,
            strengths=tuple(
                AnalysisBlock(title=item.title, explanation=item.explanation)
                for item in payload.strengths
            ),
            risks=tuple(
                AnalysisBlock(title=item.title, explanation=item.explanation)
                for item in payload.risks
            ),
            recommendations=tuple(
                AnalysisBlock(title=item.title, explanation=item.explanation)
                for item in payload.recommendations
            ),
            follow_up_question=payload.follow_up_question,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _error_code(response: httpx.Response) -> str:
        if response.status_code == 422:
            return "ai_contract_mismatch"
        try:
            code = response.json()["error"]["code"]
        except (ValueError, KeyError, TypeError):
            return "ai_unavailable"
        return code if code in KNOWN_AI_ERRORS else "ai_unavailable"

    @staticmethod
    def _to_payload(request: ConsultantRequest) -> dict[str, Any]:
        result = request.simulation_result
        simulation_result = None
        if result is not None:
            simulation_result = {
                "score_before": result.score_before,
                "score_after": result.score_after,
                "score_delta": result.score_delta,
                "districts": [
                    {
                        "district_id": item.district_id,
                        "indicators_before": {
                            code.value: value for code, value in item.indicators_before.items()
                        },
                        "indicators_after": {
                            code.value: value for code, value in item.indicators_after.items()
                        },
                        "score_before": item.score_before,
                        "score_after": item.score_after,
                    }
                    for item in result.districts
                ],
                "critical_before": [
                    {
                        "district_id": item.district_id,
                        "indicator_id": item.indicator_id.value,
                        "value": item.value,
                    }
                    for item in result.critical_before
                ],
                "critical_after": [
                    {
                        "district_id": item.district_id,
                        "indicator_id": item.indicator_id.value,
                        "value": item.value,
                    }
                    for item in result.critical_after
                ],
                "effects": [
                    {
                        "measure_ids": list(item.measure_ids),
                        "district_id": item.district_id,
                        "indicator_id": item.indicator_id.value,
                        "delta": item.delta,
                        "kind": item.kind.value,
                    }
                    for item in result.effects
                ],
            }
        return {
            "message": request.message,
            "history": [
                {"role": item.role.value, "content": item.content}
                for item in request.history
            ],
            "context": {
                "selected_measures": [
                    {
                        "measure_id": item.measure_id,
                        "district_id": item.district_id,
                    }
                    for item in request.selected_measures
                ],
                "budget_remaining": request.budget_remaining,
                "simulation_result": simulation_result,
            },
        }
