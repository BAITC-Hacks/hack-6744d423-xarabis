from typing import Annotated

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from city_simulator.domain.district_sandbox import (
    CITY_NAME,
    CRITICAL_THRESHOLD,
    IMPROVEMENTS,
    MAX_IMPROVEMENTS_PER_TURN,
    MAX_TURNS,
    QUARTERLY_INCOME,
    RULES_VERSION,
    STARTING_BUDGET,
    TARGET_VALUE,
    DistrictChoice,
    DistrictSandboxResult,
    simulate_district_sandbox,
)
from city_simulator.domain.sandbox import Improvement, SandboxValidationError

router = APIRouter(prefix="/sandbox/v2", tags=["sandbox-v2"])


class DistrictChoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    district_id: Annotated[str, Field(min_length=1, max_length=32)]
    improvement_id: Annotated[str, Field(min_length=1, max_length=32)]


class DistrictSandboxRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    turns: Annotated[
        list[Annotated[list[DistrictChoiceRequest], Field(max_length=MAX_IMPROVEMENTS_PER_TURN)]],
        Field(max_length=MAX_TURNS),
    ]


class DistrictSandboxCatalog(BaseModel):
    rules_version: str
    city_name: str
    starting_budget: int
    quarterly_income: int
    max_turns: int
    critical_threshold: int
    target_value: int
    improvements: list[Improvement]


@router.get("/catalog", response_model=DistrictSandboxCatalog)
def district_sandbox_catalog() -> DistrictSandboxCatalog:
    return DistrictSandboxCatalog(
        rules_version=RULES_VERSION,
        city_name=CITY_NAME,
        starting_budget=STARTING_BUDGET,
        quarterly_income=QUARTERLY_INCOME,
        max_turns=MAX_TURNS,
        critical_threshold=CRITICAL_THRESHOLD,
        target_value=TARGET_VALUE,
        improvements=list(IMPROVEMENTS),
    )


@router.post("/simulate", response_model=DistrictSandboxResult)
def district_sandbox_simulate(
    request: DistrictSandboxRequest,
) -> DistrictSandboxResult | JSONResponse:
    try:
        return simulate_district_sandbox(
            [
                [DistrictChoice(c.district_id, c.improvement_id) for c in turn]
                for turn in request.turns
            ]
        )
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
