from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

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
from city_simulator.domain.entities import Decision
from city_simulator.domain.scenarios import Scenario, StoredSimulationResult
from city_simulator.presentation.dependencies import (
    get_calculate_stored_scenario_use_case,
    get_create_scenario_use_case,
    get_current_result_use_case,
    get_delete_scenario_use_case,
    get_get_scenario_use_case,
    get_list_results_use_case,
    get_list_scenarios_use_case,
    get_replace_decisions_use_case,
    get_reset_scenario_use_case,
)
from city_simulator.presentation.routes import to_simulation_response
from city_simulator.presentation.scenario_schemas import (
    CalculateScenarioRequest,
    ReplaceDecisionsRequest,
    ResetScenarioRequest,
    ScenarioDecisionResponse,
    ScenarioPageResponse,
    ScenarioResponse,
    StoredSimulationResultResponse,
)
from city_simulator.presentation.schemas import ErrorResponse

router = APIRouter(prefix="/scenarios", tags=["stored scenarios"])

SCENARIO_ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Сценарий или результат не найден"},
    409: {"model": ErrorResponse, "description": "Конфликт версии сценария"},
    422: {"model": ErrorResponse, "description": "Невалидный запрос или сценарий"},
}


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


@router.get("", response_model=ScenarioPageResponse)
async def list_scenarios(
    use_case: Annotated[ListScenariosUseCase, Depends(get_list_scenarios_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ScenarioPageResponse:
    page = await use_case.execute(limit=limit, offset=offset)
    return ScenarioPageResponse(
        items=[_to_scenario_response(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/{scenario_id}",
    response_model=ScenarioResponse,
    responses=SCENARIO_ERROR_RESPONSES,
)
async def get_scenario(
    scenario_id: UUID,
    use_case: Annotated[GetScenarioUseCase, Depends(get_get_scenario_use_case)],
) -> ScenarioResponse:
    return _to_scenario_response(await use_case.execute(scenario_id))


@router.put(
    "/{scenario_id}/decisions",
    response_model=ScenarioResponse,
    responses=SCENARIO_ERROR_RESPONSES,
)
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


@router.post(
    "/{scenario_id}/reset",
    response_model=ScenarioResponse,
    responses=SCENARIO_ERROR_RESPONSES,
)
async def reset_scenario(
    scenario_id: UUID,
    payload: ResetScenarioRequest,
    use_case: Annotated[ResetScenarioUseCase, Depends(get_reset_scenario_use_case)],
) -> ScenarioResponse:
    scenario = await use_case.execute(
        scenario_id,
        expected_version=payload.expected_version,
    )
    return _to_scenario_response(scenario)


@router.delete(
    "/{scenario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=SCENARIO_ERROR_RESPONSES,
)
async def delete_scenario(
    scenario_id: UUID,
    use_case: Annotated[DeleteScenarioUseCase, Depends(get_delete_scenario_use_case)],
    expected_version: Annotated[int, Query(ge=1)],
) -> Response:
    await use_case.execute(scenario_id, expected_version=expected_version)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{scenario_id}/calculate",
    response_model=StoredSimulationResultResponse,
    responses=SCENARIO_ERROR_RESPONSES,
)
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


@router.get(
    "/{scenario_id}/result",
    response_model=StoredSimulationResultResponse,
    responses=SCENARIO_ERROR_RESPONSES,
)
async def get_current_result(
    scenario_id: UUID,
    use_case: Annotated[
        GetCurrentScenarioResultUseCase,
        Depends(get_current_result_use_case),
    ],
) -> StoredSimulationResultResponse:
    return _to_stored_result_response(await use_case.execute(scenario_id))


@router.get(
    "/{scenario_id}/results",
    response_model=list[StoredSimulationResultResponse],
    responses=SCENARIO_ERROR_RESPONSES,
)
async def list_results(
    scenario_id: UUID,
    use_case: Annotated[
        ListScenarioResultsUseCase,
        Depends(get_list_results_use_case),
    ],
) -> list[StoredSimulationResultResponse]:
    results = await use_case.execute(scenario_id)
    return [_to_stored_result_response(item) for item in results]
