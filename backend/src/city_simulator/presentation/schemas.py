from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from city_simulator.domain.enums import Direction, EffectKind, MeasureScope


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DecisionRequest(StrictModel):
    measure_id: Annotated[
        str,
        Field(pattern=r"^M[1-9][0-9]*$", max_length=8, examples=["M7"]),
    ]
    district_id: str | None = Field(default=None, examples=["nura"])


class DecisionsRequest(StrictModel):
    decisions: Annotated[list[DecisionRequest], Field(max_length=5)]


class CatalogMetadataResponse(BaseModel):
    dataset_version: str
    formula_version: str
    budget: int
    horizon_quarters: int
    required_decisions: int
    critical_threshold: float


class IndicatorResponse(BaseModel):
    id: str
    direction: Direction
    name: str
    weight: float


class DistrictResponse(BaseModel):
    id: str
    name: str
    population_share: float
    profile: str
    indicators: dict[str, float]


class MeasureResponse(BaseModel):
    id: str
    direction: Direction
    name: str
    scope: MeasureScope
    cost: int
    lag_quarters: int
    effects: dict[str, float]


class DraftValidationResponse(BaseModel):
    valid: bool = True
    decision_count: int
    total_cost: int
    remaining_budget: int
    ready_for_calculation: bool


class CriticalIndicatorResponse(BaseModel):
    district_id: str
    indicator_id: str
    value: float


class EffectResponse(BaseModel):
    measure_ids: list[str]
    district_id: str
    indicator_id: str
    delta: float
    kind: EffectKind


class DistrictResultResponse(BaseModel):
    district_id: str
    score_before: float
    score_after: float
    indicators_before: dict[str, float]
    indicators_after: dict[str, float]


class SimulationResponse(BaseModel):
    dataset_version: str
    formula_version: str
    total_cost: int
    remaining_budget: int
    score_before: float
    score_after: float
    score_delta: float
    city_average: float
    weakest_district_score: float
    districts: list[DistrictResultResponse]
    critical_before: list[CriticalIndicatorResponse]
    critical_after: list[CriticalIndicatorResponse]
    effects: list[EffectResponse]


class ErrorResponse(BaseModel):
    code: str
    details: list[str]
