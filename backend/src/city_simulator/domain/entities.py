from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from city_simulator.domain.enums import Direction, IndicatorCode, MeasureScope

IndicatorValues = Mapping[IndicatorCode, float]


@dataclass(frozen=True, slots=True)
class District:
    id: str
    name: str
    population_share: float
    indicators: IndicatorValues
    profile: str


@dataclass(frozen=True, slots=True)
class Measure:
    id: str
    direction: Direction
    name: str
    scope: MeasureScope
    cost: int
    lag_quarters: int
    effects: IndicatorValues

    def realized_effects(self, horizon_quarters: int) -> IndicatorValues:
        factor = (horizon_quarters - self.lag_quarters) / horizon_quarters
        return MappingProxyType({code: value * factor for code, value in self.effects.items()})


@dataclass(frozen=True, slots=True)
class Decision:
    measure_id: str
    district_id: str | None = None


@dataclass(frozen=True, slots=True)
class DistrictResult:
    district_id: str
    district_name: str
    score_before: float
    score_after: float
    indicators_before: IndicatorValues
    indicators_after: IndicatorValues


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    total_cost: int
    remaining_budget: int
    score_before: float
    score_after: float
    score_delta: float
    city_average: float
    weakest_district_score: float
    critical_indicators_count: int
    districts: tuple[DistrictResult, ...]


@dataclass(frozen=True, slots=True)
class ScenarioAnalysis:
    summary: str
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
