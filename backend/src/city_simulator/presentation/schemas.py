from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from city_simulator.domain.enums import Direction, MeasureScope


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DecisionRequest(StrictModel):
    measure_id: Annotated[str, Field(min_length=2, max_length=3, examples=["M7"])]
    district_id: str | None = Field(default=None, examples=["nura"])


class SimulateRequest(StrictModel):
    decisions: Annotated[list[DecisionRequest], Field(min_length=1, max_length=14)]


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


class DistrictResultResponse(BaseModel):
    district_id: str
    district_name: str
    score_before: float
    score_after: float
    score_delta: float
    indicators_before: dict[str, float]
    indicators_after: dict[str, float]
    indicator_deltas: dict[str, float]


class AnalysisResponse(BaseModel):
    summary: str
    strengths: list[str]
    risks: list[str]
    recommendations: list[str]


class SimulationResponse(BaseModel):
    total_cost: int
    remaining_budget: int
    score_before: float
    score_after: float
    score_delta: float
    city_average: float
    weakest_district_score: float
    critical_indicators_count: int
    districts: list[DistrictResultResponse]
    analysis: AnalysisResponse


class ErrorResponse(BaseModel):
    code: str
    details: list[str]
