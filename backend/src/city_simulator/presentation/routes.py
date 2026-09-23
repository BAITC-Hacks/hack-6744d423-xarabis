from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from city_simulator.application.use_cases import (
    GetCatalogUseCase,
    SimulateScenarioUseCase,
    ValidateDraftScenarioUseCase,
)
from city_simulator.domain.entities import Decision, ScenarioResult
from city_simulator.infrastructure.database import get_db_session
from city_simulator.presentation.dependencies import (
    get_catalog_use_case,
    get_simulate_use_case,
    get_validate_draft_use_case,
)
from city_simulator.presentation.schemas import (
    CatalogMetadataResponse,
    CriticalIndicatorResponse,
    DecisionsRequest,
    DistrictResponse,
    DistrictResultResponse,
    DraftValidationResponse,
    EffectResponse,
    ErrorResponse,
    IndicatorResponse,
    MeasureResponse,
    SimulationResponse,
)

router = APIRouter()

VALIDATION_ERROR_RESPONSE = {
    422: {"model": ErrorResponse, "description": "Невалидный запрос или сценарий"}
}


def _to_decisions(payload: DecisionsRequest) -> list[Decision]:
    return [
        Decision(measure_id=item.measure_id.upper(), district_id=item.district_id)
        for item in payload.decisions
    ]


def to_simulation_response(result: ScenarioResult) -> SimulationResponse:
    return SimulationResponse(
        dataset_version=result.dataset_version,
        formula_version=result.formula_version,
        total_cost=result.total_cost,
        remaining_budget=result.remaining_budget,
        score_before=round(result.score_before, 2),
        score_after=round(result.score_after, 2),
        score_delta=round(result.score_delta, 2),
        city_average=round(result.city_average, 2),
        weakest_district_score=round(result.weakest_district_score, 2),
        districts=[
            DistrictResultResponse(
                district_id=item.district_id,
                score_before=round(item.score_before, 2),
                score_after=round(item.score_after, 2),
                indicators_before={
                    code.value: value for code, value in item.indicators_before.items()
                },
                indicators_after={
                    code.value: round(value, 4) for code, value in item.indicators_after.items()
                },
            )
            for item in result.districts
        ],
        critical_before=[
            CriticalIndicatorResponse(
                district_id=item.district_id,
                indicator_id=item.indicator_id.value,
                value=round(item.value, 4),
            )
            for item in result.critical_before
        ],
        critical_after=[
            CriticalIndicatorResponse(
                district_id=item.district_id,
                indicator_id=item.indicator_id.value,
                value=round(item.value, 4),
            )
            for item in result.critical_after
        ],
        effects=[
            EffectResponse(
                measure_ids=list(item.measure_ids),
                district_id=item.district_id,
                indicator_id=item.indicator_id.value,
                delta=round(item.delta, 4),
                kind=item.kind,
            )
            for item in result.effects
        ],
    )


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/ready",
    tags=["system"],
    response_model=None,
    responses={503: {"description": "PostgreSQL недоступен"}},
)
async def readiness(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str] | JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@router.get("/catalog", response_model=CatalogMetadataResponse, tags=["catalog"])
def get_catalog(
    use_case: Annotated[GetCatalogUseCase, Depends(get_catalog_use_case)],
) -> CatalogMetadataResponse:
    dataset = use_case.dataset()
    return CatalogMetadataResponse(
        dataset_version=dataset.dataset_version,
        formula_version=dataset.formula_version,
        budget=dataset.rules.budget,
        horizon_quarters=dataset.rules.horizon_quarters,
        required_decisions=dataset.rules.required_decisions,
        max_measures_per_direction=dataset.rules.max_measures_per_direction,
        critical_threshold=dataset.rules.critical_threshold,
    )


@router.get("/indicators", response_model=list[IndicatorResponse], tags=["catalog"])
def list_indicators(
    use_case: Annotated[GetCatalogUseCase, Depends(get_catalog_use_case)],
) -> list[IndicatorResponse]:
    dataset = use_case.dataset()
    return [
        IndicatorResponse(
            id=item.id.value,
            direction=item.direction,
            name=item.name,
            scale_description=item.scale_description,
            weight=dataset.rules.indicator_weights[item.id],
        )
        for item in dataset.indicators
    ]


@router.get("/districts", response_model=list[DistrictResponse], tags=["catalog"])
def list_districts(
    use_case: Annotated[GetCatalogUseCase, Depends(get_catalog_use_case)],
) -> list[DistrictResponse]:
    return [
        DistrictResponse(
            id=item.id,
            name=item.name,
            population_share=item.population_share,
            profile=item.profile,
            indicators={code.value: value for code, value in item.indicators.items()},
        )
        for item in use_case.dataset().districts
    ]


@router.get("/measures", response_model=list[MeasureResponse], tags=["catalog"])
def list_measures(
    use_case: Annotated[GetCatalogUseCase, Depends(get_catalog_use_case)],
) -> list[MeasureResponse]:
    return [
        MeasureResponse(
            id=item.id,
            direction=item.direction,
            name=item.name,
            scope=item.scope,
            cost=item.cost,
            lag_quarters=item.lag_quarters,
            effects={code.value: value for code, value in item.effects.items()},
        )
        for item in use_case.dataset().measures
    ]


@router.post(
    "/scenarios/validate",
    response_model=DraftValidationResponse,
    responses=VALIDATION_ERROR_RESPONSE,
    tags=["simulation"],
)
def validate_draft(
    payload: DecisionsRequest,
    use_case: Annotated[
        ValidateDraftScenarioUseCase,
        Depends(get_validate_draft_use_case),
    ],
) -> DraftValidationResponse:
    result = use_case.execute(_to_decisions(payload))
    return DraftValidationResponse(
        decision_count=result.decision_count,
        total_cost=result.total_cost,
        remaining_budget=result.remaining_budget,
        ready_for_calculation=result.ready_for_calculation,
    )


@router.post(
    "/scenarios/simulate",
    response_model=SimulationResponse,
    responses=VALIDATION_ERROR_RESPONSE,
    tags=["simulation"],
)
def simulate(
    payload: DecisionsRequest,
    use_case: Annotated[SimulateScenarioUseCase, Depends(get_simulate_use_case)],
) -> SimulationResponse:
    return to_simulation_response(use_case.execute(_to_decisions(payload)))
