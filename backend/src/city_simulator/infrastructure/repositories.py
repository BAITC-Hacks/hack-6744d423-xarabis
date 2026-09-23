import json
import math
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from city_simulator.domain.entities import (
    District,
    Incompatibility,
    Indicator,
    Measure,
    SimulationDataset,
    SimulationRules,
    Synergy,
)
from city_simulator.domain.enums import (
    ConflictScope,
    Direction,
    IndicatorCode,
    MeasureScope,
)
from city_simulator.domain.exceptions import DatasetConfigurationError
from city_simulator.domain.ports import CityDataRepository


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _RulesData(_StrictModel):
    budget: int = Field(gt=0)
    horizon_quarters: int = Field(gt=0)
    required_decisions: int = Field(gt=0)
    max_measures_per_direction: int = Field(gt=0)
    critical_threshold: float = Field(ge=0, le=100, allow_inf_nan=False)
    city_average_weight: float = Field(ge=0, le=1, allow_inf_nan=False)
    weakest_district_weight: float = Field(ge=0, le=1, allow_inf_nan=False)
    critical_penalty: float = Field(ge=0, allow_inf_nan=False)
    indicator_weights: dict[IndicatorCode, float]


class _IndicatorData(_StrictModel):
    id: IndicatorCode
    direction: Direction
    name: str = Field(min_length=1)
    scale_description: str = Field(min_length=1)


class _DistrictData(_StrictModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    population_share: float = Field(gt=0, le=1, allow_inf_nan=False)
    profile: str = Field(min_length=1)
    indicators: dict[IndicatorCode, float]


class _MeasureData(_StrictModel):
    id: str = Field(pattern=r"^M[1-9][0-9]*$")
    direction: Direction
    name: str = Field(min_length=1)
    scope: MeasureScope
    cost: int = Field(gt=0)
    lag_quarters: int = Field(ge=0)
    effects: dict[IndicatorCode, float]


class _SynergyData(_StrictModel):
    measure_ids: tuple[str, str]
    target_measure_id: str
    indicator_id: IndicatorCode
    delta: float = Field(allow_inf_nan=False)


class _IncompatibilityData(_StrictModel):
    measure_ids: tuple[str, str]
    scope: ConflictScope


class _DatasetData(_StrictModel):
    dataset_version: str = Field(min_length=1)
    formula_version: str = Field(min_length=1)
    rules: _RulesData
    indicators: list[_IndicatorData]
    districts: list[_DistrictData]
    measures: list[_MeasureData]
    synergies: list[_SynergyData]
    incompatibilities: list[_IncompatibilityData]

    @model_validator(mode="after")
    def validate_references(self) -> "_DatasetData":
        indicator_ids = {item.id for item in self.indicators}
        district_ids = [item.id for item in self.districts]
        measure_ids = [item.id for item in self.measures]

        self._require_unique("indicator", [item.id.value for item in self.indicators])
        self._require_unique("district", district_ids)
        self._require_unique("measure", measure_ids)

        if indicator_ids != set(IndicatorCode):
            raise ValueError("dataset must define all ten supported indicators")
        if set(self.rules.indicator_weights) != indicator_ids:
            raise ValueError("indicator_weights must contain every indicator exactly once")
        if any(
            not math.isfinite(value) or value < 0 for value in self.rules.indicator_weights.values()
        ):
            raise ValueError("indicator weights must be finite and non-negative")
        if not math.isclose(sum(self.rules.indicator_weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError("indicator weights must sum to 1")
        if not math.isclose(
            self.rules.city_average_weight + self.rules.weakest_district_weight,
            1.0,
            abs_tol=1e-9,
        ):
            raise ValueError("city and weakest-district weights must sum to 1")
        if not math.isclose(
            sum(district.population_share for district in self.districts),
            1.0,
            abs_tol=1e-9,
        ):
            raise ValueError("district population shares must sum to 1")

        for district in self.districts:
            if set(district.indicators) != indicator_ids:
                raise ValueError(f"district {district.id} must contain every indicator")
            if any(
                not math.isfinite(value) or value < 0 or value > 100
                for value in district.indicators.values()
            ):
                raise ValueError(f"district {district.id} indicators must be between 0 and 100")

        measure_id_set = set(measure_ids)
        measure_by_id = {measure.id: measure for measure in self.measures}
        for measure in self.measures:
            if measure.lag_quarters > self.rules.horizon_quarters:
                raise ValueError(f"measure {measure.id} lag exceeds simulation horizon")
            if not measure.effects or not set(measure.effects) <= indicator_ids:
                raise ValueError(f"measure {measure.id} has invalid effects")
            if any(not math.isfinite(value) for value in measure.effects.values()):
                raise ValueError(f"measure {measure.id} effects must be finite")

        for synergy in self.synergies:
            if not set(synergy.measure_ids) <= measure_id_set:
                raise ValueError("synergy references an unknown measure")
            if synergy.target_measure_id not in synergy.measure_ids:
                raise ValueError("synergy target must be one of its measures")
            if measure_by_id[synergy.target_measure_id].scope is not MeasureScope.DISTRICT:
                raise ValueError("synergy target measure must have district scope")

        for conflict in self.incompatibilities:
            if not set(conflict.measure_ids) <= measure_id_set:
                raise ValueError("incompatibility references an unknown measure")
            if conflict.scope is ConflictScope.SAME_DISTRICT and any(
                measure_by_id[item].scope is not MeasureScope.DISTRICT
                for item in conflict.measure_ids
            ):
                raise ValueError("same-district incompatibility requires district measures")
        return self

    @staticmethod
    def _require_unique(kind: str, values: list[str]) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {kind} id")


class VersionedJsonCityDataRepository(CityDataRepository):
    def __init__(self, dataset_path: Path | None = None) -> None:
        self._dataset_path = dataset_path
        self._dataset: SimulationDataset | None = None

    def get_dataset(self) -> SimulationDataset:
        if self._dataset is not None:
            return self._dataset
        try:
            if self._dataset_path is None:
                resource = files("city_simulator.resources").joinpath("simulation.v1.json")
                raw = resource.read_text(encoding="utf-8")
            else:
                raw = self._dataset_path.read_text(encoding="utf-8")
            data = _DatasetData.model_validate(json.loads(raw))
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise DatasetConfigurationError(f"Invalid simulation dataset: {exc}") from exc
        self._dataset = self._to_domain(data)
        return self._dataset

    @staticmethod
    def _to_domain(data: _DatasetData) -> SimulationDataset:
        return SimulationDataset(
            dataset_version=data.dataset_version,
            formula_version=data.formula_version,
            rules=SimulationRules(
                budget=data.rules.budget,
                horizon_quarters=data.rules.horizon_quarters,
                required_decisions=data.rules.required_decisions,
                max_measures_per_direction=data.rules.max_measures_per_direction,
                critical_threshold=data.rules.critical_threshold,
                city_average_weight=data.rules.city_average_weight,
                weakest_district_weight=data.rules.weakest_district_weight,
                critical_penalty=data.rules.critical_penalty,
                indicator_weights=MappingProxyType(dict(data.rules.indicator_weights)),
            ),
            indicators=tuple(
                Indicator(
                    id=item.id,
                    direction=item.direction,
                    name=item.name,
                    scale_description=item.scale_description,
                )
                for item in data.indicators
            ),
            districts=tuple(
                District(
                    id=item.id,
                    name=item.name,
                    population_share=item.population_share,
                    indicators=MappingProxyType(dict(item.indicators)),
                    profile=item.profile,
                )
                for item in data.districts
            ),
            measures=tuple(
                Measure(
                    id=item.id,
                    direction=item.direction,
                    name=item.name,
                    scope=item.scope,
                    cost=item.cost,
                    lag_quarters=item.lag_quarters,
                    effects=MappingProxyType(dict(item.effects)),
                )
                for item in data.measures
            ),
            synergies=tuple(
                Synergy(
                    measure_ids=item.measure_ids,
                    target_measure_id=item.target_measure_id,
                    indicator_id=item.indicator_id,
                    delta=item.delta,
                )
                for item in data.synergies
            ),
            incompatibilities=tuple(
                Incompatibility(measure_ids=item.measure_ids, scope=item.scope)
                for item in data.incompatibilities
            ),
        )
