from collections.abc import Sequence

from city_simulator.domain.entities import Decision, Measure, ScenarioAnalysis, ScenarioResult
from city_simulator.domain.ports import ScenarioAnalyst


class RuleBasedScenarioAnalyst(ScenarioAnalyst):
    """Deterministic fallback; can be replaced by an LLM adapter through the same port."""

    def analyze(
        self,
        result: ScenarioResult,
        decisions: Sequence[Decision],
        measures: Sequence[Measure],
    ) -> ScenarioAnalysis:
        improved = sorted(
            result.districts,
            key=lambda district: district.score_after - district.score_before,
            reverse=True,
        )
        strengths = [
            f"Наибольший прирост у района {item.district_name}: "
            f"+{item.score_after - item.score_before:.2f} балла."
            for item in improved[:2]
            if item.score_after > item.score_before
        ]
        if result.score_delta > 0:
            strengths.insert(0, f"Общий Score вырос на {result.score_delta:.2f} балла.")

        weakest = min(result.districts, key=lambda district: district.score_after)
        risks = [
            f"Самым слабым остаётся район {weakest.district_name}: {weakest.score_after:.2f} балла."
        ]
        if result.critical_indicators_count:
            risks.append(
                "После решений остаётся критических показателей: "
                f"{result.critical_indicators_count}."
            )
        if result.remaining_budget:
            risks.append(f"Неиспользованный бюджет: {result.remaining_budget} единиц.")

        selected_directions = {measure.direction for measure in measures}
        recommendations = ["Сравните сценарий с альтернативой, направленной на самый слабый район."]
        if len(selected_directions) < 5:
            recommendations.append(
                "Проверьте, не остаётся ли без внимания одно из направлений развития."
            )
        if result.critical_indicators_count:
            recommendations.append("При следующем выборе сначала устраните показатели ниже 40.")

        return ScenarioAnalysis(
            summary=(
                f"Выбрано {len(decisions)} мероприятий стоимостью {result.total_cost}. "
                f"Итоговый Astana Quality of Life Score: {result.score_after:.2f}."
            ),
            strengths=tuple(strengths or ["Сценарий сохраняет исходный уровень качества жизни."]),
            risks=tuple(risks),
            recommendations=tuple(recommendations),
        )
