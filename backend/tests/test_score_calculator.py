from collections import Counter
from dataclasses import replace
from itertools import combinations
from types import MappingProxyType

import pytest

from city_simulator.domain.entities import Decision
from city_simulator.domain.enums import EffectKind, IndicatorCode
from city_simulator.domain.services import CalculationScenarioValidator, ScoreCalculator


def test_baseline_score_matches_dataset(dataset) -> None:
    result = ScoreCalculator().calculate((), dataset)
    assert result.score_before == pytest.approx(52.55768)
    assert result.score_after == pytest.approx(52.55768)
    assert {item.district_id: item.score_before for item in result.districts} == pytest.approx(
        {
            "esil": 62.99,
            "almaty": 57.06,
            "saryarka": 54.65,
            "baikonur": 56.63,
            "nura": 49.18,
        }
    )
    assert len(result.critical_before) == 2
    assert result.critical_before == result.critical_after


def test_example_scenario_matches_document(dataset, example_decisions) -> None:
    CalculationScenarioValidator().validate(example_decisions, dataset)
    result = ScoreCalculator().calculate(example_decisions, dataset)

    assert result.total_cost == 95
    assert result.remaining_budget == 5
    assert result.score_after == pytest.approx(56.54307)
    assert result.score_delta == pytest.approx(3.98539)
    assert result.city_average == pytest.approx(58.0776)
    assert result.weakest_district_score == pytest.approx(52.9625)
    assert result.critical_after == ()
    assert any(
        effect.kind is EffectKind.SYNERGY
        and effect.measure_ids == ("M10", "M12")
        and effect.district_id == "nura"
        and effect.delta == 2
        for effect in result.effects
    )
    for district in result.districts:
        assert all(0 <= value <= 100 for value in district.indicators_after.values())
        for indicator_id, before in district.indicators_before.items():
            traced_delta = sum(
                effect.delta
                for effect in result.effects
                if effect.district_id == district.district_id
                and effect.indicator_id is indicator_id
            )
            assert district.indicators_after[indicator_id] - before == pytest.approx(traced_delta)


def test_lag_scales_a_district_effect(dataset) -> None:
    result = ScoreCalculator().calculate((Decision("M1", "esil"),), dataset)
    esil = next(item for item in result.districts if item.district_id == "esil")
    assert esil.indicators_after[IndicatorCode.T1] == pytest.approx(49.5)
    assert esil.indicators_after[IndicatorCode.T2] == pytest.approx(68.75)


def test_city_measure_affects_every_district(dataset) -> None:
    result = ScoreCalculator().calculate((Decision("M12"),), dataset)
    for district in result.districts:
        assert (
            district.indicators_after[IndicatorCode.C2]
            - district.indicators_before[IndicatorCode.C2]
        ) == pytest.approx(4.375)


def test_synergy_is_fixed_and_not_scaled_by_lag(dataset) -> None:
    result = ScoreCalculator().calculate(
        (Decision("M10", "nura"), Decision("M12")),
        dataset,
    )
    nura = next(item for item in result.districts if item.district_id == "nura")
    assert nura.indicators_after[IndicatorCode.B1] == pytest.approx(67.5)


def test_clipping_is_reflected_in_effect_trace(dataset) -> None:
    esil = dataset.get_district("esil")
    assert esil is not None
    indicators = dict(esil.indicators)
    indicators[IndicatorCode.T1] = 99
    modified_esil = replace(esil, indicators=MappingProxyType(indicators))
    modified_dataset = replace(
        dataset,
        districts=(modified_esil, *dataset.districts[1:]),
    )

    result = ScoreCalculator().calculate((Decision("M1", "esil"),), modified_dataset)
    esil_result = result.districts[0]
    t1_effect = next(
        item
        for item in result.effects
        if item.district_id == "esil" and item.indicator_id is IndicatorCode.T1
    )
    assert esil_result.indicators_after[IndicatorCode.T1] == 100
    assert t1_effect.delta == pytest.approx(1.0)


def test_decision_order_does_not_change_result(dataset, example_decisions) -> None:
    calculator = ScoreCalculator()
    forward = calculator.calculate(example_decisions, dataset)
    backward = calculator.calculate(tuple(reversed(example_decisions)), dataset)
    assert forward.score_after == backward.score_after
    assert [item.indicators_after for item in forward.districts] == [
        item.indicators_after for item in backward.districts
    ]
    assert forward.effects == backward.effects


def test_different_valid_decisions_change_score(dataset, example_decisions) -> None:
    alternative = (
        Decision("M9", "nura"),
        Decision("M11", "esil"),
        Decision("M10", "almaty"),
        Decision("M12"),
        Decision("M4", "saryarka"),
    )
    CalculationScenarioValidator().validate(alternative, dataset)
    calculator = ScoreCalculator()
    assert (
        calculator.calculate(alternative, dataset).score_after
        != calculator.calculate(example_decisions, dataset).score_after
    )


def test_documented_minimum_cost_valid_plan_costs_61(dataset) -> None:
    decisions = (
        Decision("M9", "nura"),
        Decision("M11", "nura"),
        Decision("M10", "nura"),
        Decision("M12"),
        Decision("M4", "saryarka"),
    )
    CalculationScenarioValidator().validate(decisions, dataset)
    assert ScoreCalculator().calculate(decisions, dataset).total_cost == 61

    candidate_costs = [
        sum(measure.cost for measure in measures)
        for measures in combinations(dataset.measures, dataset.rules.required_decisions)
        if max(Counter(measure.direction for measure in measures).values())
        <= dataset.rules.max_measures_per_direction
        and not {"M1", "M3"} <= {measure.id for measure in measures}
    ]
    assert min(candidate_costs) == 61


def test_values_equal_to_critical_threshold_are_not_critical(dataset) -> None:
    nura = dataset.get_district("nura")
    assert nura is not None
    indicators = dict(nura.indicators)
    indicators[IndicatorCode.S1] = dataset.rules.critical_threshold
    indicators[IndicatorCode.S2] = dataset.rules.critical_threshold
    modified_nura = replace(nura, indicators=MappingProxyType(indicators))
    modified_dataset = replace(dataset, districts=(*dataset.districts[:-1], modified_nura))

    result = ScoreCalculator().calculate((), modified_dataset)

    assert result.critical_before == ()
