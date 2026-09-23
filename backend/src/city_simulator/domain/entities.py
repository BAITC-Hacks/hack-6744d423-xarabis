from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from city_simulator.domain.enums import (
    ConflictScope,
    Direction,
    EffectKind,
    IndicatorCode,
    MeasureScope,
)

IndicatorValues = Mapping[IndicatorCode, float]


@dataclass(frozen=True, slots=True)
class Indicator:
    id: IndicatorCode
    direction: Direction
    name: str
    scale_description: str


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
class Synergy:
    measure_ids: tuple[str, str]
    target_measure_id: str
    indicator_id: IndicatorCode
    delta: float


@dataclass(frozen=True, slots=True)
class Incompatibility:
    measure_ids: tuple[str, str]
    scope: ConflictScope


@dataclass(frozen=True, slots=True)
class SimulationRules:
    budget: int
    horizon_quarters: int
    required_decisions: int
    max_measures_per_direction: int
    critical_threshold: float
    city_average_weight: float
    weakest_district_weight: float
    critical_penalty: float
    indicator_weights: IndicatorValues


@dataclass(frozen=True, slots=True)
class SimulationDataset:
    dataset_version: str
    formula_version: str
    rules: SimulationRules
    indicators: tuple[Indicator, ...]
    districts: tuple[District, ...]
    measures: tuple[Measure, ...]
    synergies: tuple[Synergy, ...]
    incompatibilities: tuple[Incompatibility, ...]

    def get_measure(self, measure_id: str) -> Measure | None:
        normalized = measure_id.upper()
        return next((measure for measure in self.measures if measure.id == normalized), None)

    def get_district(self, district_id: str) -> District | None:
        return next((district for district in self.districts if district.id == district_id), None)


@dataclass(frozen=True, slots=True)
class CriticalIndicator:
    district_id: str
    indicator_id: IndicatorCode
    value: float


@dataclass(frozen=True, slots=True)
class EffectTrace:
    measure_ids: tuple[str, ...]
    district_id: str
    indicator_id: IndicatorCode
    delta: float
    kind: EffectKind


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
    dataset_version: str
    formula_version: str
    total_cost: int
    remaining_budget: int
    score_before: float
    score_after: float
    score_delta: float
    city_average: float
    weakest_district_score: float
    districts: tuple[DistrictResult, ...]
    critical_before: tuple[CriticalIndicator, ...]
    critical_after: tuple[CriticalIndicator, ...]
    effects: tuple[EffectTrace, ...]
