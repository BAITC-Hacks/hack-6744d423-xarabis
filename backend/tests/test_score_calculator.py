import pytest

from city_simulator.domain.entities import Decision
from city_simulator.domain.exceptions import ScenarioValidationError
from city_simulator.domain.services import ScenarioValidator, ScoreCalculator
from city_simulator.infrastructure.repositories import DISTRICTS, MEASURES

EXAMPLE_DECISIONS = (
    Decision("M7", "nura"),
    Decision("M8", "nura"),
    Decision("M10", "nura"),
    Decision("M12"),
    Decision("M5", "saryarka"),
)


def test_baseline_score_matches_dataset() -> None:
    result = ScoreCalculator().calculate((), DISTRICTS, MEASURES)
    assert result.score_before == pytest.approx(52.56, abs=0.01)
    assert result.score_after == pytest.approx(52.56, abs=0.01)


def test_example_scenario_is_valid_and_improves_score() -> None:
    ScenarioValidator().validate(EXAMPLE_DECISIONS, DISTRICTS, MEASURES)
    result = ScoreCalculator().calculate(EXAMPLE_DECISIONS, DISTRICTS, MEASURES)

    assert result.total_cost == 95
    assert result.remaining_budget == 5
    assert result.score_after == pytest.approx(56.54, abs=0.01)
    assert result.score_delta > 0
    assert result.critical_indicators_count == 0


def test_validator_rejects_budget_and_duplicate_measure() -> None:
    invalid = (
        Decision("M3", "yesil"),
        Decision("M3", "nura"),
        Decision("M7", "nura"),
        Decision("M8", "nura"),
        Decision("M13", "almaty"),
    )

    with pytest.raises(ScenarioValidationError) as error:
        ScenarioValidator().validate(invalid, DISTRICTS, MEASURES)

    assert any("повторно" in item for item in error.value.errors)
    assert any("Бюджет превышен" in item for item in error.value.errors)


def test_validator_rejects_district_for_city_measure() -> None:
    invalid = (
        Decision("M9", "nura"),
        Decision("M10", "nura"),
        Decision("M11", "yesil"),
        Decision("M12", "nura"),
        Decision("M4", "saryarka"),
    )

    with pytest.raises(ScenarioValidationError) as error:
        ScenarioValidator().validate(invalid, DISTRICTS, MEASURES)

    assert any("городской меры M12" in item for item in error.value.errors)
