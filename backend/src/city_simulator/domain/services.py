from collections import Counter
from collections.abc import Mapping, Sequence

from city_simulator.domain.entities import (
    Decision,
    District,
    DistrictResult,
    Measure,
    ScenarioResult,
)
from city_simulator.domain.enums import IndicatorCode, MeasureScope
from city_simulator.domain.exceptions import ScenarioValidationError

INDICATOR_WEIGHTS: dict[IndicatorCode, float] = {
    IndicatorCode.T1: 0.10,
    IndicatorCode.T2: 0.10,
    IndicatorCode.E1: 0.09,
    IndicatorCode.E2: 0.11,
    IndicatorCode.S1: 0.11,
    IndicatorCode.S2: 0.11,
    IndicatorCode.B1: 0.09,
    IndicatorCode.B2: 0.09,
    IndicatorCode.C1: 0.10,
    IndicatorCode.C2: 0.10,
}


class ScenarioValidator:
    def __init__(self, *, budget: int = 100, required_decisions: int = 5) -> None:
        self.budget = budget
        self.required_decisions = required_decisions

    def validate(
        self,
        decisions: Sequence[Decision],
        districts: Sequence[District],
        measures: Sequence[Measure],
    ) -> None:
        errors: list[str] = []
        district_ids = {district.id for district in districts}
        measure_by_id = {measure.id: measure for measure in measures}
        selected_ids = [decision.measure_id.upper() for decision in decisions]

        if len(decisions) != self.required_decisions:
            errors.append(f"Нужно выбрать ровно {self.required_decisions} мероприятий")
        if len(selected_ids) != len(set(selected_ids)):
            errors.append("Одно мероприятие нельзя выбирать повторно")

        selected_measures: list[Measure] = []
        for decision in decisions:
            measure = measure_by_id.get(decision.measure_id.upper())
            if measure is None:
                errors.append(f"Неизвестное мероприятие: {decision.measure_id}")
                continue
            selected_measures.append(measure)
            if measure.scope is MeasureScope.DISTRICT:
                if decision.district_id not in district_ids:
                    errors.append(f"Для {measure.id} нужно указать существующий район")
            elif decision.district_id is not None:
                errors.append(f"Для городской меры {measure.id} район указывать нельзя")

        total_cost = sum(measure.cost for measure in selected_measures)
        if total_cost > self.budget:
            errors.append(f"Бюджет превышен: {total_cost} из {self.budget}")

        direction_counts = Counter(measure.direction for measure in selected_measures)
        for direction, count in direction_counts.items():
            if count > 2:
                errors.append(f"В направлении '{direction.value}' выбрано больше 2 мероприятий")

        selected = set(selected_ids)
        if {"M1", "M3"} <= selected:
            errors.append("M1 и M3 несовместимы")

        decision_by_measure = {decision.measure_id.upper(): decision for decision in decisions}
        for first, second in (("M4", "M7"), ("M5", "M13")):
            if {first, second} <= selected:
                if (
                    decision_by_measure[first].district_id
                    == decision_by_measure[second].district_id
                ):
                    errors.append(f"{first} и {second} нельзя применять в одном районе")

        if errors:
            raise ScenarioValidationError(errors)


class ScoreCalculator:
    def __init__(self, *, budget: int = 100, horizon_quarters: int = 8) -> None:
        self.budget = budget
        self.horizon_quarters = horizon_quarters

    @staticmethod
    def district_score(indicators: Mapping[IndicatorCode, float]) -> float:
        return sum(INDICATOR_WEIGHTS[code] * indicators[code] for code in INDICATOR_WEIGHTS)

    def calculate(
        self,
        decisions: Sequence[Decision],
        districts: Sequence[District],
        measures: Sequence[Measure],
    ) -> ScenarioResult:
        measure_by_id = {measure.id: measure for measure in measures}
        updated = {
            district.id: {code: float(value) for code, value in district.indicators.items()}
            for district in districts
        }

        for decision in decisions:
            measure = measure_by_id[decision.measure_id.upper()]
            targets = (
                districts
                if measure.scope is MeasureScope.CITY
                else (next(item for item in districts if item.id == decision.district_id),)
            )
            for target in targets:
                for code, effect in measure.realized_effects(self.horizon_quarters).items():
                    updated[target.id][code] += effect

        self._apply_synergies(decisions, updated)

        for values in updated.values():
            for code in values:
                values[code] = min(100.0, max(0.0, values[code]))

        district_results = tuple(
            DistrictResult(
                district_id=district.id,
                district_name=district.name,
                score_before=self.district_score(district.indicators),
                score_after=self.district_score(updated[district.id]),
                indicators_before=district.indicators,
                indicators_after=updated[district.id],
            )
            for district in districts
        )
        city_average = sum(
            district.population_share * result.score_after
            for district, result in zip(districts, district_results, strict=True)
        )
        weakest_score = min(result.score_after for result in district_results)
        critical_count = sum(value < 40 for values in updated.values() for value in values.values())
        score_after = 0.7 * city_average + 0.3 * weakest_score - critical_count
        score_before = self._baseline_score(districts)
        total_cost = sum(measure_by_id[item.measure_id.upper()].cost for item in decisions)

        return ScenarioResult(
            total_cost=total_cost,
            remaining_budget=self.budget - total_cost,
            score_before=score_before,
            score_after=score_after,
            score_delta=score_after - score_before,
            city_average=city_average,
            weakest_district_score=weakest_score,
            critical_indicators_count=critical_count,
            districts=district_results,
        )

    def _baseline_score(self, districts: Sequence[District]) -> float:
        scores = [self.district_score(district.indicators) for district in districts]
        average = sum(
            district.population_share * score
            for district, score in zip(districts, scores, strict=True)
        )
        critical = sum(
            value < 40 for district in districts for value in district.indicators.values()
        )
        return 0.7 * average + 0.3 * min(scores) - critical

    @staticmethod
    def _apply_synergies(
        decisions: Sequence[Decision],
        updated: dict[str, dict[IndicatorCode, float]],
    ) -> None:
        by_measure = {decision.measure_id.upper(): decision for decision in decisions}
        synergies = (
            ("M1", "M2", IndicatorCode.T1, 2.0),
            ("M10", "M12", IndicatorCode.B1, 2.0),
            ("M5", "M6", IndicatorCode.E2, 2.0),
        )
        for first, second, indicator, bonus in synergies:
            if first in by_measure and second in by_measure:
                district_id = by_measure[first].district_id
                if district_id is not None:
                    updated[district_id][indicator] += bonus
