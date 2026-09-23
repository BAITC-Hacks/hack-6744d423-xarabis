from functools import lru_cache

from city_simulator.application.use_cases import (
    GetCatalogUseCase,
    SimulateScenarioUseCase,
    ValidateDraftScenarioUseCase,
)
from city_simulator.domain.services import (
    CalculationScenarioValidator,
    DraftScenarioValidator,
    ScoreCalculator,
)
from city_simulator.infrastructure.repositories import VersionedJsonCityDataRepository


@lru_cache
def get_repository() -> VersionedJsonCityDataRepository:
    return VersionedJsonCityDataRepository()


def get_catalog_use_case() -> GetCatalogUseCase:
    return GetCatalogUseCase(get_repository())


def get_simulate_use_case() -> SimulateScenarioUseCase:
    return SimulateScenarioUseCase(
        repository=get_repository(),
        validator=CalculationScenarioValidator(),
        calculator=ScoreCalculator(),
    )


def get_validate_draft_use_case() -> ValidateDraftScenarioUseCase:
    return ValidateDraftScenarioUseCase(
        repository=get_repository(),
        validator=DraftScenarioValidator(),
    )
