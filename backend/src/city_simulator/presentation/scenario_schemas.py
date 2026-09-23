from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from city_simulator.domain.enums import ScenarioStatus
from city_simulator.presentation.schemas import DecisionRequest, SimulationResponse, StrictModel


class ScenarioDecisionResponse(StrictModel):
    measure_id: str
    district_id: str | None


class ScenarioResponse(StrictModel):
    id: UUID
    status: ScenarioStatus
    version: int
    budget_limit: int
    decisions: list[ScenarioDecisionResponse]
    created_at: datetime
    updated_at: datetime


class ScenarioPageResponse(StrictModel):
    items: list[ScenarioResponse]
    total: int
    limit: int
    offset: int


class ReplaceDecisionsRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]
    decisions: list[DecisionRequest]


class CalculateScenarioRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]


class ResetScenarioRequest(StrictModel):
    expected_version: Annotated[int, Field(ge=1)]


class StoredSimulationResultResponse(StrictModel):
    id: UUID
    scenario_id: UUID
    scenario_version: int
    created_at: datetime
    simulation: SimulationResponse
