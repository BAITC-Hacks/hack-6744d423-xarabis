import pytest

from city_simulator.domain.entities import Decision
from city_simulator.domain.exceptions import ScenarioValidationError
from city_simulator.domain.services import (
    CalculationScenarioValidator,
    DraftScenarioValidator,
)


def _issues(validator, decisions, dataset):
    with pytest.raises(ScenarioValidationError) as error:
        validator.validate(decisions, dataset)
    return error.value.issues


def test_draft_allows_an_empty_or_partial_selection(dataset) -> None:
    validator = DraftScenarioValidator()
    validator.validate((), dataset)
    validator.validate((Decision("M12"), Decision("M10", "nura")), dataset)


def test_calculation_requires_exactly_five_decisions(dataset) -> None:
    issues = _issues(CalculationScenarioValidator(), (Decision("M12"),), dataset)
    assert issues[0].code == "decision_count_mismatch"
    assert issues[0].message == "Нужно выбрать ровно 5 мероприятий"
    assert issues[0].context == {"required": 5, "actual": 1}


@pytest.mark.parametrize(
    ("decisions", "code", "message"),
    [
        ((Decision("M99", "nura"),), "unknown_measure", "Неизвестное мероприятие"),
        ((Decision("M12", "nura"),), "district_not_allowed", "городской меры M12"),
        ((Decision("M7"),), "district_required", "Для M7 нужно указать"),
        (
            (Decision("M7", "nura"), Decision("M7", "esil")),
            "duplicate_measure",
            "повторно",
        ),
        (
            (Decision("M7", "esil"), Decision("M8", "nura"), Decision("M9", "almaty")),
            "direction_limit_exceeded",
            "направлении 'social'",
        ),
        (
            (Decision("M1", "esil"), Decision("M3", "nura")),
            "incompatible_measures",
            "M1 и M3 несовместимы",
        ),
        (
            (Decision("M4", "nura"), Decision("M7", "nura")),
            "incompatible_measures",
            "M4 и M7 нельзя применять в одном районе",
        ),
        (
            (Decision("M5", "esil"), Decision("M13", "esil")),
            "incompatible_measures",
            "M5 и M13 нельзя применять в одном районе",
        ),
    ],
)
def test_draft_validator_rejects_rule_violations(
    dataset,
    decisions,
    code,
    message,
) -> None:
    issues = _issues(DraftScenarioValidator(), decisions, dataset)
    assert any(issue.code == code and message in issue.message for issue in issues)


def test_same_district_conflict_allows_different_districts(dataset) -> None:
    DraftScenarioValidator().validate(
        (Decision("M4", "nura"), Decision("M7", "esil")),
        dataset,
    )


def test_budget_is_checked_for_a_draft(dataset) -> None:
    decisions = (
        Decision("M3", "esil"),
        Decision("M7", "nura"),
        Decision("M8", "nura"),
        Decision("M13", "almaty"),
        Decision("M2"),
    )
    issues = _issues(DraftScenarioValidator(), decisions, dataset)
    budget_issue = next(issue for issue in issues if issue.code == "budget_exceeded")
    assert budget_issue.message == "Бюджет превышен: 124 из 100"
    assert budget_issue.context == {"total_cost": 124, "budget": 100}
