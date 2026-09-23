from collections.abc import Sequence
from dataclasses import dataclass

from city_simulator.domain.entities import Decision, ScenarioResult, SimulationDataset
from city_simulator.domain.ports import CityDataRepository
from city_simulator.domain.services import (
    CalculationScenarioValidator,
    DraftScenarioValidator,
    ScoreCalculator,
)


@dataclass(frozen=True, slots=True)
class DraftValidationOutput:
    decision_count: int
    total_cost: int
    remaining_budget: int
    ready_for_calculation: bool


class GetCatalogUseCase:
    def __init__(self, repository: CityDataRepository) -> None:
        self.repository = repository

    def dataset(self) -> SimulationDataset:
        return self.repository.get_dataset()


class ValidateDraftScenarioUseCase:
    def __init__(
        self,
        repository: CityDataRepository,
        validator: DraftScenarioValidator,
    ) -> None:
        self.repository = repository
        self.validator = validator

    def execute(self, decisions: Sequence[Decision]) -> DraftValidationOutput:
        dataset = self.repository.get_dataset()
        self.validator.validate(decisions, dataset)
        measure_by_id = {measure.id: measure for measure in dataset.measures}
        total_cost = sum(measure_by_id[item.measure_id.upper()].cost for item in decisions)
        return DraftValidationOutput(
            decision_count=len(decisions),
            total_cost=total_cost,
            remaining_budget=dataset.rules.budget - total_cost,
            ready_for_calculation=len(decisions) == dataset.rules.required_decisions,
        )


class SimulateScenarioUseCase:
    def __init__(
        self,
        repository: CityDataRepository,
        validator: CalculationScenarioValidator,
        calculator: ScoreCalculator,
    ) -> None:
        self.repository = repository
        self.validator = validator
        self.calculator = calculator

    def execute(self, decisions: Sequence[Decision]) -> ScenarioResult:
        dataset = self.repository.get_dataset()
        self.validator.validate(decisions, dataset)
        return self.calculator.calculate(decisions, dataset)
