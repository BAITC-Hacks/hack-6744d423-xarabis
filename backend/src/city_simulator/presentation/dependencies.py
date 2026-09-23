from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from city_simulator.application.scenarios import (
    CalculateStoredScenarioUseCase,
    CreateScenarioUseCase,
    DeleteScenarioUseCase,
    GetCurrentScenarioResultUseCase,
    GetScenarioUseCase,
    ListScenarioResultsUseCase,
    ListScenariosUseCase,
    ReplaceScenarioDecisionsUseCase,
    ResetScenarioUseCase,
)
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
from city_simulator.infrastructure.database import get_db_session
from city_simulator.infrastructure.repositories import VersionedJsonCityDataRepository
from city_simulator.infrastructure.scenario_repository import SqlAlchemyScenarioRepository


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


def get_scenario_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SqlAlchemyScenarioRepository:
    return SqlAlchemyScenarioRepository(session)


def get_create_scenario_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> CreateScenarioUseCase:
    return CreateScenarioUseCase(scenarios, get_repository())


def get_get_scenario_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> GetScenarioUseCase:
    return GetScenarioUseCase(scenarios)


def get_list_scenarios_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> ListScenariosUseCase:
    return ListScenariosUseCase(scenarios)


def get_replace_decisions_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> ReplaceScenarioDecisionsUseCase:
    return ReplaceScenarioDecisionsUseCase(
        scenarios,
        get_repository(),
        DraftScenarioValidator(),
    )


def get_reset_scenario_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> ResetScenarioUseCase:
    return ResetScenarioUseCase(scenarios)


def get_delete_scenario_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> DeleteScenarioUseCase:
    return DeleteScenarioUseCase(scenarios)


def get_calculate_stored_scenario_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> CalculateStoredScenarioUseCase:
    return CalculateStoredScenarioUseCase(
        scenarios,
        get_repository(),
        CalculationScenarioValidator(),
        ScoreCalculator(),
    )


def get_current_result_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> GetCurrentScenarioResultUseCase:
    return GetCurrentScenarioResultUseCase(scenarios)


def get_list_results_use_case(
    scenarios: Annotated[SqlAlchemyScenarioRepository, Depends(get_scenario_repository)],
) -> ListScenarioResultsUseCase:
    return ListScenarioResultsUseCase(scenarios)
