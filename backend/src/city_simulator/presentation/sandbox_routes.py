from typing import Annotated

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from city_simulator.domain.sandbox import (
    CITY_NAME,
    CRITICAL_THRESHOLD,
    IMPROVEMENTS,
    MAX_TURNS,
    QUARTERLY_INCOME,
    STARTING_BUDGET,
    TARGET_VALUE,
    Improvement,
    SandboxResult,
    SandboxValidationError,
    simulate_sandbox,
)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class SandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turns: Annotated[
        list[Annotated[list[Annotated[str, Field(max_length=32)]], Field(max_length=3)]],
        Field(max_length=MAX_TURNS),
    ]


class SandboxCatalog(BaseModel):
    city_name: str
    starting_budget: int
    quarterly_income: int
    max_turns: int
    critical_threshold: int
    target_value: int
    improvements: list[Improvement]


@router.get("/catalog", response_model=SandboxCatalog)
def sandbox_catalog() -> SandboxCatalog:
    return SandboxCatalog(
        city_name=CITY_NAME,
        starting_budget=STARTING_BUDGET,
        quarterly_income=QUARTERLY_INCOME,
        max_turns=MAX_TURNS,
        critical_threshold=CRITICAL_THRESHOLD,
        target_value=TARGET_VALUE,
        improvements=list(IMPROVEMENTS),
    )


@router.post("/simulate", response_model=SandboxResult)
def sandbox_simulate(request: SandboxRequest) -> SandboxResult | JSONResponse:
    try:
        return simulate_sandbox(request.turns)
    except SandboxValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "sandbox_validation_error",
                    "message": str(exc),
                    "details": [str(exc)],
                }
            },
        )
