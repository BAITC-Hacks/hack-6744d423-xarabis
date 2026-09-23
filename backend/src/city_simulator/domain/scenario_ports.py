from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from city_simulator.domain.entities import Decision, ScenarioResult
from city_simulator.domain.scenarios import Scenario, StoredSimulationResult


class ScenarioRepository(ABC):
    @abstractmethod
    async def create(self, *, budget_limit: int) -> Scenario: ...

    @abstractmethod
    async def get(self, scenario_id: UUID) -> Scenario | None: ...

    @abstractmethod
    async def list(self, *, limit: int, offset: int) -> Sequence[Scenario]: ...

    @abstractmethod
    async def count(self) -> int: ...

    @abstractmethod
    async def replace_decisions(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
        decisions: Sequence[Decision],
    ) -> Scenario: ...

    @abstractmethod
    async def save_result(
        self,
        scenario_id: UUID,
        *,
        expected_version: int,
        result: ScenarioResult,
    ) -> StoredSimulationResult: ...

    @abstractmethod
    async def get_current_result(self, scenario_id: UUID) -> StoredSimulationResult | None: ...

    @abstractmethod
    async def list_results(self, scenario_id: UUID) -> Sequence[StoredSimulationResult]: ...

    @abstractmethod
    async def delete(self, scenario_id: UUID, *, expected_version: int) -> None: ...
