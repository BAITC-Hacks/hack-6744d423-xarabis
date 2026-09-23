from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from city_simulator.application.scenarios import (
    CalculateStoredScenarioUseCase,
    CreateScenarioUseCase,
    GetCurrentScenarioResultUseCase,
    GetScenarioUseCase,
    ListScenarioResultsUseCase,
    ReplaceScenarioDecisionsUseCase,
)
from city_simulator.domain.entities import Decision
from city_simulator.domain.scenarios import Scenario, StoredSimulationResult
from city_simulator.presentation.dependencies import (
    get_calculate_stored_scenario_use_case,
    get_create_scenario_use_case,
    get_current_result_use_case,
    get_get_scenario_use_case,
    get_list_results_use_case,
    get_replace_decisions_use_case,
)
from city_simulator.presentation.routes import to_simulation_response
from city_simulator.presentation.scenario_schemas import (
    CalculateScenarioRequest,
    ReplaceDecisionsRequest,
    ScenarioDecisionResponse,
    ScenarioResponse,
    StoredSimulationResultResponse,
)

router = APIRouter(prefix="/scenarios", tags=["stored scenarios"])


def _to_scenario_response(scenario: Scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=scenario.id,
        status=scenario.status,
        version=scenario.version,
        budget_limit=scenario.budget_limit,
        decisions=[
            ScenarioDecisionResponse(
                measure_id=item.measure_id,
                district_id=item.district_id,
            )
            for item in scenario.decisions
        ],
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


def _to_stored_result_response(
    result: StoredSimulationResult,
) -> StoredSimulationResultResponse:
    return StoredSimulationResultResponse(
        id=result.id,
        scenario_id=result.scenario_id,
        scenario_version=result.scenario_version,
        created_at=result.created_at,
        simulation=to_simulation_response(result.result),
    )


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    use_case: Annotated[CreateScenarioUseCase, Depends(get_create_scenario_use_case)],
) -> ScenarioResponse:
    return _to_scenario_response(await use_case.execute())


@router.get("/{scenario_id}", response_model=ScenarioResponse)
async def get_scenario(
    scenario_id: UUID,
    use_case: Annotated[GetScenarioUseCase, Depends(get_get_scenario_use_case)],
) -> ScenarioResponse:
    return _to_scenario_response(await use_case.execute(scenario_id))


@router.put("/{scenario_id}/decisions", response_model=ScenarioResponse)
async def replace_decisions(
    scenario_id: UUID,
    payload: ReplaceDecisionsRequest,
    use_case: Annotated[
        ReplaceScenarioDecisionsUseCase,
        Depends(get_replace_decisions_use_case),
    ],
) -> ScenarioResponse:
    scenario = await use_case.execute(
        scenario_id,
        expected_version=payload.expected_version,
        decisions=[
            Decision(item.measure_id.upper(), item.district_id) for item in payload.decisions
        ],
    )
    return _to_scenario_response(scenario)


@router.post("/{scenario_id}/calculate", response_model=StoredSimulationResultResponse)
async def calculate_scenario(
    scenario_id: UUID,
    payload: CalculateScenarioRequest,
    use_case: Annotated[
        CalculateStoredScenarioUseCase,
        Depends(get_calculate_stored_scenario_use_case),
    ],
) -> StoredSimulationResultResponse:
    result = await use_case.execute(
        scenario_id,
        expected_version=payload.expected_version,
    )
    return _to_stored_result_response(result)


@router.get("/{scenario_id}/result", response_model=StoredSimulationResultResponse)
async def get_current_result(
    scenario_id: UUID,
    use_case: Annotated[
        GetCurrentScenarioResultUseCase,
        Depends(get_current_result_use_case),
    ],
) -> StoredSimulationResultResponse:
    return _to_stored_result_response(await use_case.execute(scenario_id))


@router.get("/{scenario_id}/results", response_model=list[StoredSimulationResultResponse])
async def list_results(
    scenario_id: UUID,
    use_case: Annotated[
        ListScenarioResultsUseCase,
        Depends(get_list_results_use_case),
    ],
) -> list[StoredSimulationResultResponse]:
    results = await use_case.execute(scenario_id)
    return [_to_stored_result_response(item) for item in results]
