from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from city_simulator.domain.entities import Decision
from city_simulator.domain.exceptions import (
    ScenarioNotFoundError,
    ScenarioVersionConflictError,
    SimulationResultNotFoundError,
)
from city_simulator.domain.ports import CityDataRepository
from city_simulator.domain.scenario_ports import ScenarioRepository
from city_simulator.domain.scenarios import Scenario, StoredSimulationResult
from city_simulator.domain.services import (
    CalculationScenarioValidator,
    DraftScenarioValidator,
    ScoreCalculator,
)


class CreateScenarioUseCase:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        city_data: CityDataRepository,
    ) -> None:
        self._scenarios = scenarios
        self._city_data = city_data

    async def execute(self) -> Scenario:
        budget = self._city_data.get_dataset().rules.budget
        return await self._scenarios.create(budget_limit=budget)


class GetScenarioUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, scenario_id: UUID) -> Scenario:
        scenario = await self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)
        return scenario


@dataclass(frozen=True, slots=True)
class ScenarioPage:
    items: Sequence[Scenario]
    total: int
    limit: int
    offset: int


class ListScenariosUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, *, limit: int, offset: int) -> ScenarioPage:
        items = await self._scenarios.list(limit=limit, offset=offset)
        total = await self._scenarios.count()
        return ScenarioPage(items=items, total=total, limit=limit, offset=offset)


class ReplaceScenarioDecisionsUseCase:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        city_data: CityDataRepository,
        validator: DraftScenarioValidator,
    ) -> None:
        self._scenarios = scenarios
        self._city_data = city_data
        self._validator = validator

    async def execute(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
        decisions: Sequence[Decision],
    ) -> Scenario:
        self._validator.validate(decisions, self._city_data.get_dataset())
        return await self._scenarios.replace_decisions(
            scenario_id,
            expected_version=expected_version,
            decisions=decisions,
        )


class ResetScenarioUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, scenario_id: UUID, *, expected_version: int) -> Scenario:
        return await self._scenarios.replace_decisions(
            scenario_id,
            expected_version=expected_version,
            decisions=(),
        )


class DeleteScenarioUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, scenario_id: UUID, *, expected_version: int) -> None:
        await self._scenarios.delete(scenario_id, expected_version=expected_version)


class CalculateStoredScenarioUseCase:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        city_data: CityDataRepository,
        validator: CalculationScenarioValidator,
        calculator: ScoreCalculator,
    ) -> None:
        self._scenarios = scenarios
        self._city_data = city_data
        self._validator = validator
        self._calculator = calculator

    async def execute(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
    ) -> StoredSimulationResult:
        scenario = await self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)
        if scenario.version != expected_version:
            raise ScenarioVersionConflictError(
                scenario_id,
                expected_version=expected_version,
                current_version=scenario.version,
            )
        dataset = self._city_data.get_dataset()
        self._validator.validate(scenario.decisions, dataset)
        result = self._calculator.calculate(scenario.decisions, dataset)
        return await self._scenarios.save_result(
            scenario_id,
            expected_version=expected_version,
            result=result,
        )


class GetCurrentScenarioResultUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, scenario_id: UUID) -> StoredSimulationResult:
        scenario = await self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)
        result = await self._scenarios.get_current_result(scenario_id)
        if result is None:
            raise SimulationResultNotFoundError(scenario_id)
        return result


class ListScenarioResultsUseCase:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    async def execute(self, scenario_id: UUID) -> Sequence[StoredSimulationResult]:
        scenario = await self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)
        return await self._scenarios.list_results(scenario_id)
