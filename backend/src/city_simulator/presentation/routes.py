from typing import Annotated

from fastapi import APIRouter, Depends

from city_simulator.application.use_cases import GetCatalogUseCase, SimulateScenarioUseCase
from city_simulator.domain.entities import Decision
from city_simulator.presentation.dependencies import get_catalog_use_case, get_simulate_use_case
from city_simulator.presentation.schemas import (
    AnalysisResponse,
    DistrictResponse,
    DistrictResultResponse,
    MeasureResponse,
    SimulateRequest,
    SimulationResponse,
)

router = APIRouter()


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


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
        for item in use_case.districts()
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
        for item in use_case.measures()
    ]


@router.post("/scenarios/simulate", response_model=SimulationResponse, tags=["simulation"])
def simulate(
    payload: SimulateRequest,
    use_case: Annotated[SimulateScenarioUseCase, Depends(get_simulate_use_case)],
) -> SimulationResponse:
    output = use_case.execute(
        [
            Decision(measure_id=item.measure_id.upper(), district_id=item.district_id)
            for item in payload.decisions
        ]
    )
    result = output.result
    return SimulationResponse(
        total_cost=result.total_cost,
        remaining_budget=result.remaining_budget,
        score_before=round(result.score_before, 2),
        score_after=round(result.score_after, 2),
        score_delta=round(result.score_delta, 2),
        city_average=round(result.city_average, 2),
        weakest_district_score=round(result.weakest_district_score, 2),
        critical_indicators_count=result.critical_indicators_count,
        districts=[
            DistrictResultResponse(
                district_id=item.district_id,
                district_name=item.district_name,
                score_before=round(item.score_before, 2),
                score_after=round(item.score_after, 2),
                score_delta=round(item.score_after - item.score_before, 2),
                indicators_before={
                    code.value: value for code, value in item.indicators_before.items()
                },
                indicators_after={
                    code.value: round(value, 2) for code, value in item.indicators_after.items()
                },
                indicator_deltas={
                    code.value: round(item.indicators_after[code] - before, 2)
                    for code, before in item.indicators_before.items()
                },
            )
            for item in result.districts
        ],
        analysis=AnalysisResponse(
            summary=output.analysis.summary,
            strengths=list(output.analysis.strengths),
            risks=list(output.analysis.risks),
            recommendations=list(output.analysis.recommendations),
        ),
    )
