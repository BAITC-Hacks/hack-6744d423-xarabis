from typing import Any

from city_simulator.domain.entities import (
    CriticalIndicator,
    DistrictResult,
    EffectTrace,
    ScenarioResult,
)
from city_simulator.domain.enums import EffectKind, IndicatorCode


def result_to_payload(result: ScenarioResult) -> dict[str, Any]:
    return {
        "dataset_version": result.dataset_version,
        "formula_version": result.formula_version,
        "total_cost": result.total_cost,
        "remaining_budget": result.remaining_budget,
        "score_before": result.score_before,
        "score_after": result.score_after,
        "score_delta": result.score_delta,
        "city_average": result.city_average,
        "weakest_district_score": result.weakest_district_score,
        "districts": [
            {
                "district_id": district.district_id,
                "district_name": district.district_name,
                "score_before": district.score_before,
                "score_after": district.score_after,
                "indicators_before": {
                    code.value: value for code, value in district.indicators_before.items()
                },
                "indicators_after": {
                    code.value: value for code, value in district.indicators_after.items()
                },
            }
            for district in result.districts
        ],
        "critical_before": [
            {
                "district_id": item.district_id,
                "indicator_id": item.indicator_id.value,
                "value": item.value,
            }
            for item in result.critical_before
        ],
        "critical_after": [
            {
                "district_id": item.district_id,
                "indicator_id": item.indicator_id.value,
                "value": item.value,
            }
            for item in result.critical_after
        ],
        "effects": [
            {
                "measure_ids": list(item.measure_ids),
                "district_id": item.district_id,
                "indicator_id": item.indicator_id.value,
                "delta": item.delta,
                "kind": item.kind.value,
            }
            for item in result.effects
        ],
    }


def payload_to_result(payload: dict[str, Any]) -> ScenarioResult:
    return ScenarioResult(
        dataset_version=payload["dataset_version"],
        formula_version=payload["formula_version"],
        total_cost=payload["total_cost"],
        remaining_budget=payload["remaining_budget"],
        score_before=payload["score_before"],
        score_after=payload["score_after"],
        score_delta=payload["score_delta"],
        city_average=payload["city_average"],
        weakest_district_score=payload["weakest_district_score"],
        districts=tuple(
            DistrictResult(
                district_id=item["district_id"],
                district_name=item["district_name"],
                score_before=item["score_before"],
                score_after=item["score_after"],
                indicators_before={
                    IndicatorCode(code): value for code, value in item["indicators_before"].items()
                },
                indicators_after={
                    IndicatorCode(code): value for code, value in item["indicators_after"].items()
                },
            )
            for item in payload["districts"]
        ),
        critical_before=tuple(
            CriticalIndicator(
                district_id=item["district_id"],
                indicator_id=IndicatorCode(item["indicator_id"]),
                value=item["value"],
            )
            for item in payload["critical_before"]
        ),
        critical_after=tuple(
            CriticalIndicator(
                district_id=item["district_id"],
                indicator_id=IndicatorCode(item["indicator_id"]),
                value=item["value"],
            )
            for item in payload["critical_after"]
        ),
        effects=tuple(
            EffectTrace(
                measure_ids=tuple(item["measure_ids"]),
                district_id=item["district_id"],
                indicator_id=IndicatorCode(item["indicator_id"]),
                delta=item["delta"],
                kind=EffectKind(item["kind"]),
            )
            for item in payload["effects"]
        ),
    )
