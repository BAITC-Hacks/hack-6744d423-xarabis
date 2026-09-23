from collections.abc import Sequence
from dataclasses import dataclass

from city_simulator.domain.entities import (
    Decision,
    District,
    Measure,
    ScenarioAnalysis,
    ScenarioResult,
)
from city_simulator.domain.ports import CityDataRepository, ScenarioAnalyst
from city_simulator.domain.services import ScenarioValidator, ScoreCalculator


@dataclass(frozen=True, slots=True)
class SimulationOutput:
    result: ScenarioResult
    analysis: ScenarioAnalysis


class GetCatalogUseCase:
    def __init__(self, repository: CityDataRepository) -> None:
        self.repository = repository

    def districts(self) -> Sequence[District]:
        return self.repository.list_districts()

    def measures(self) -> Sequence[Measure]:
        return self.repository.list_measures()


class SimulateScenarioUseCase:
    def __init__(
        self,
        repository: CityDataRepository,
        validator: ScenarioValidator,
        calculator: ScoreCalculator,
        analyst: ScenarioAnalyst,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.calculator = calculator
        self.analyst = analyst

    def execute(self, decisions: Sequence[Decision]) -> SimulationOutput:
        districts = self.repository.list_districts()
        measures = self.repository.list_measures()
        self.validator.validate(decisions, districts, measures)
        result = self.calculator.calculate(decisions, districts, measures)
        selected = [self.repository.get_measure(item.measure_id.upper()) for item in decisions]
        analysis = self.analyst.analyze(
            result,
            decisions,
            [measure for measure in selected if measure is not None],
        )
        return SimulationOutput(result=result, analysis=analysis)
