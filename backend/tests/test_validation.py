import pytest

from city_simulator.domain.entities import Decision
from city_simulator.domain.exceptions import ScenarioValidationError
from city_simulator.domain.services import (
    CalculationScenarioValidator,
    DraftScenarioValidator,
)


def _errors(validator, decisions, dataset) -> list[str]:
    with pytest.raises(ScenarioValidationError) as error:
        validator.validate(decisions, dataset)
    return error.value.errors


def test_draft_allows_an_empty_or_partial_selection(dataset) -> None:
    validator = DraftScenarioValidator()
    validator.validate((), dataset)
    validator.validate((Decision("M12"), Decision("M10", "nura")), dataset)


def test_calculation_requires_exactly_five_decisions(dataset) -> None:
    errors = _errors(CalculationScenarioValidator(), (Decision("M12"),), dataset)
    assert errors[0] == "Нужно выбрать ровно 5 мероприятий"


@pytest.mark.parametrize(
    ("decisions", "message"),
    [
        ((Decision("M99", "nura"),), "Неизвестное мероприятие"),
        ((Decision("M12", "nura"),), "городской меры M12"),
        ((Decision("M7"),), "Для M7 нужно указать"),
        ((Decision("M7", "nura"), Decision("M7", "esil")), "повторно"),
        (
            (Decision("M1", "esil"), Decision("M2"), Decision("M3", "nura")),
            "направлении 'transport'",
        ),
        ((Decision("M1", "esil"), Decision("M3", "nura")), "M1 и M3 несовместимы"),
        (
            (Decision("M4", "nura"), Decision("M7", "nura")),
            "M4 и M7 нельзя применять в одном районе",
        ),
        (
            (Decision("M5", "esil"), Decision("M13", "esil")),
            "M5 и M13 нельзя применять в одном районе",
        ),
    ],
)
def test_draft_validator_rejects_rule_violations(dataset, decisions, message) -> None:
    errors = _errors(DraftScenarioValidator(), decisions, dataset)
    assert any(message in item for item in errors)


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
    errors = _errors(DraftScenarioValidator(), decisions, dataset)
    assert any("Бюджет превышен: 124 из 100" in item for item in errors)
