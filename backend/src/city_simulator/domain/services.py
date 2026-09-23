from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace

from city_simulator.domain.entities import (
    CriticalIndicator,
    Decision,
    District,
    DistrictResult,
    EffectTrace,
    ScenarioResult,
    SimulationDataset,
)
from city_simulator.domain.enums import ConflictScope, EffectKind, IndicatorCode, MeasureScope
from city_simulator.domain.exceptions import ScenarioValidationError


class DraftScenarioValidator:
    """Validates a partial selection while a user is building a scenario."""

    def validate(self, decisions: Sequence[Decision], dataset: SimulationDataset) -> None:
        errors: list[str] = []
        rules = dataset.rules
        normalized_ids = [decision.measure_id.upper() for decision in decisions]
        measure_by_id = {measure.id: measure for measure in dataset.measures}
        district_ids = {district.id for district in dataset.districts}

        if len(decisions) > rules.required_decisions:
            errors.append(f"Можно выбрать не более {rules.required_decisions} мероприятий")
        if len(normalized_ids) != len(set(normalized_ids)):
            errors.append("Одно мероприятие нельзя выбирать повторно")

        selected_measures = []
        decision_by_measure: dict[str, Decision] = {}
        for decision, measure_id in zip(decisions, normalized_ids, strict=True):
            measure = measure_by_id.get(measure_id)
            if measure is None:
                errors.append(f"Неизвестное мероприятие: {decision.measure_id}")
                continue
            selected_measures.append(measure)
            decision_by_measure[measure_id] = decision
            if measure.scope is MeasureScope.DISTRICT:
                if decision.district_id not in district_ids:
                    errors.append(f"Для {measure.id} нужно указать существующий район")
            elif decision.district_id is not None:
                errors.append(f"Для городской меры {measure.id} район указывать нельзя")

        total_cost = sum(measure.cost for measure in selected_measures)
        if total_cost > rules.budget:
            errors.append(f"Бюджет превышен: {total_cost} из {rules.budget}")

        direction_counts = Counter(measure.direction for measure in selected_measures)
        for direction, count in direction_counts.items():
            if count > rules.max_measures_per_direction:
                errors.append(
                    f"В направлении '{direction.value}' выбрано больше "
                    f"{rules.max_measures_per_direction} мероприятий"
                )

        selected_ids = set(decision_by_measure)
        for conflict in dataset.incompatibilities:
            first, second = conflict.measure_ids
            if not {first, second} <= selected_ids:
                continue
            if conflict.scope is ConflictScope.GLOBAL:
                errors.append(f"{first} и {second} несовместимы")
            elif decision_by_measure[first].district_id == decision_by_measure[second].district_id:
                errors.append(f"{first} и {second} нельзя применять в одном районе")

        if errors:
            raise ScenarioValidationError(errors)


class CalculationScenarioValidator:
    """Adds final calculation requirements to the partial-selection rules."""

    def __init__(self, draft_validator: DraftScenarioValidator | None = None) -> None:
        self._draft_validator = draft_validator or DraftScenarioValidator()

    def validate(self, decisions: Sequence[Decision], dataset: SimulationDataset) -> None:
        errors: list[str] = []
        try:
            self._draft_validator.validate(decisions, dataset)
        except ScenarioValidationError as exc:
            errors.extend(exc.errors)
        if len(decisions) != dataset.rules.required_decisions:
            errors.insert(0, f"Нужно выбрать ровно {dataset.rules.required_decisions} мероприятий")
        if errors:
            raise ScenarioValidationError(errors)


class ScoreCalculator:
    """Pure deterministic simulation engine with an auditable effect trace."""

    def calculate(
        self,
        decisions: Sequence[Decision],
        dataset: SimulationDataset,
    ) -> ScenarioResult:
        rules = dataset.rules
        measure_by_id = {measure.id: measure for measure in dataset.measures}
        district_by_id = {district.id: district for district in dataset.districts}
        normalized_decisions = tuple(
            Decision(item.measure_id.upper(), item.district_id) for item in decisions
        )

        raw_effects: list[EffectTrace] = []
        for decision in normalized_decisions:
            measure = measure_by_id[decision.measure_id]
            target_ids = (
                tuple(district_by_id)
                if measure.scope is MeasureScope.CITY
                else (decision.district_id,)
            )
            for district_id in target_ids:
                if district_id is None:
                    continue
                for indicator_id, delta in measure.realized_effects(rules.horizon_quarters).items():
                    raw_effects.append(
                        EffectTrace(
                            measure_ids=(measure.id,),
                            district_id=district_id,
                            indicator_id=indicator_id,
                            delta=delta,
                            kind=EffectKind.DIRECT,
                        )
                    )

        selected = {item.measure_id: item for item in normalized_decisions}
        for synergy in dataset.synergies:
            if not set(synergy.measure_ids) <= set(selected):
                continue
            district_id = selected[synergy.target_measure_id].district_id
            if district_id is not None:
                raw_effects.append(
                    EffectTrace(
                        measure_ids=synergy.measure_ids,
                        district_id=district_id,
                        indicator_id=synergy.indicator_id,
                        delta=synergy.delta,
                        kind=EffectKind.SYNERGY,
                    )
                )

        effects, updated = self._apply_effects(dataset.districts, raw_effects)
        district_results = tuple(
            DistrictResult(
                district_id=district.id,
                district_name=district.name,
                score_before=self._district_score(district.indicators, dataset),
                score_after=self._district_score(updated[district.id], dataset),
                indicators_before=district.indicators,
                indicators_after=updated[district.id],
            )
            for district in dataset.districts
        )
        critical_before = self._critical_indicators(
            ((district.id, district.indicators) for district in dataset.districts), dataset
        )
        critical_after = self._critical_indicators(updated.items(), dataset)
        score_before, _, _ = self._city_score(
            dataset.districts,
            tuple(result.score_before for result in district_results),
            len(critical_before),
            dataset,
        )
        score_after, city_average, weakest_score = self._city_score(
            dataset.districts,
            tuple(result.score_after for result in district_results),
            len(critical_after),
            dataset,
        )
        total_cost = sum(measure_by_id[item.measure_id].cost for item in normalized_decisions)

        return ScenarioResult(
            dataset_version=dataset.dataset_version,
            formula_version=dataset.formula_version,
            total_cost=total_cost,
            remaining_budget=rules.budget - total_cost,
            score_before=score_before,
            score_after=score_after,
            score_delta=score_after - score_before,
            city_average=city_average,
            weakest_district_score=weakest_score,
            districts=district_results,
            critical_before=critical_before,
            critical_after=critical_after,
            effects=effects,
        )

    @staticmethod
    def _apply_effects(
        districts: Sequence[District],
        raw_effects: Sequence[EffectTrace],
    ) -> tuple[tuple[EffectTrace, ...], dict[str, dict[IndicatorCode, float]]]:
        updated = {
            district.id: {code: float(value) for code, value in district.indicators.items()}
            for district in districts
        }
        grouped: dict[tuple[str, IndicatorCode], list[int]] = defaultdict(list)
        for index, effect in enumerate(raw_effects):
            grouped[(effect.district_id, effect.indicator_id)].append(index)

        normalized_effects = list(raw_effects)
        for (district_id, indicator_id), indexes in grouped.items():
            base = updated[district_id][indicator_id]
            raw_delta = sum(raw_effects[index].delta for index in indexes)
            final_value = min(100.0, max(0.0, base + raw_delta))
            applied_delta = final_value - base
            if raw_delta != 0 and applied_delta != raw_delta:
                factor = applied_delta / raw_delta
                for index in indexes:
                    normalized_effects[index] = replace(
                        raw_effects[index], delta=raw_effects[index].delta * factor
                    )
            updated[district_id][indicator_id] = final_value
        ordered_effects = tuple(
            sorted(
                normalized_effects,
                key=lambda item: (
                    item.district_id,
                    item.indicator_id.value,
                    item.kind.value,
                    item.measure_ids,
                ),
            )
        )
        return ordered_effects, updated

    @staticmethod
    def _district_score(
        indicators: Mapping[IndicatorCode, float],
        dataset: SimulationDataset,
    ) -> float:
        return sum(
            dataset.rules.indicator_weights[code] * indicators[code]
            for code in dataset.rules.indicator_weights
        )

    @staticmethod
    def _critical_indicators(
        districts: Iterable[tuple[str, Mapping[IndicatorCode, float]]],
        dataset: SimulationDataset,
    ) -> tuple[CriticalIndicator, ...]:
        threshold = dataset.rules.critical_threshold
        return tuple(
            CriticalIndicator(
                district_id=district_id,
                indicator_id=indicator_id,
                value=value,
            )
            for district_id, indicators in districts
            for indicator_id, value in indicators.items()
            if value < threshold
        )

    @staticmethod
    def _city_score(
        districts: Sequence[District],
        district_scores: Sequence[float],
        critical_count: int,
        dataset: SimulationDataset,
    ) -> tuple[float, float, float]:
        city_average = sum(
            district.population_share * score
            for district, score in zip(districts, district_scores, strict=True)
        )
        weakest_score = min(district_scores)
        rules = dataset.rules
        score = (
            rules.city_average_weight * city_average
            + rules.weakest_district_weight * weakest_score
            - rules.critical_penalty * critical_count
        )
        return score, city_average, weakest_score
