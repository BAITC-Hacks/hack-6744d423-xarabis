from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from city_simulator.domain.entities import Decision, ScenarioResult
from city_simulator.domain.enums import ScenarioStatus


@dataclass(frozen=True, slots=True)
class Scenario:
    id: UUID
    status: ScenarioStatus
    version: int
    budget_limit: int
    decisions: tuple[Decision, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredSimulationResult:
    id: UUID
    scenario_id: UUID
    scenario_version: int
    result: ScenarioResult
    created_at: datetime
