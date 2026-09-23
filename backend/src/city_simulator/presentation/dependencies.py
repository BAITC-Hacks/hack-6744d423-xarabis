from functools import lru_cache

from city_simulator.application.use_cases import GetCatalogUseCase, SimulateScenarioUseCase
from city_simulator.domain.services import ScenarioValidator, ScoreCalculator
from city_simulator.infrastructure.analysis import RuleBasedScenarioAnalyst
from city_simulator.infrastructure.repositories import InMemoryCityDataRepository


@lru_cache
def get_repository() -> InMemoryCityDataRepository:
    return InMemoryCityDataRepository()


def get_catalog_use_case() -> GetCatalogUseCase:
    return GetCatalogUseCase(get_repository())


def get_simulate_use_case() -> SimulateScenarioUseCase:
    return SimulateScenarioUseCase(
        repository=get_repository(),
        validator=ScenarioValidator(),
        calculator=ScoreCalculator(),
        analyst=RuleBasedScenarioAnalyst(),
    )
