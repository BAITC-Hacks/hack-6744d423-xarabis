from dataclasses import dataclass, field
from typing import Any


class DomainError(Exception):
    """Base error for an expected business-rule violation."""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)


class ScenarioValidationError(DomainError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        # Kept as a convenience for logs and existing domain-level callers.
        self.errors = [issue.message for issue in issues]
        super().__init__("; ".join(self.errors))


class DatasetConfigurationError(DomainError):
    """Raised when the versioned simulation dataset is internally inconsistent."""


class ScenarioNotFoundError(DomainError):
    def __init__(self, scenario_id: object) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"Сценарий {scenario_id} не найден")


class ScenarioVersionConflictError(DomainError):
    def __init__(
        self,
        scenario_id: object,
        *,
        expected_version: int | None = None,
        current_version: int | None = None,
    ) -> None:
        self.scenario_id = scenario_id
        self.expected_version = expected_version
        self.current_version = current_version
        super().__init__("Сценарий уже изменён другим запросом; обновите данные и повторите")


class SimulationResultNotFoundError(DomainError):
    def __init__(self, scenario_id: object) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"Для текущей версии сценария {scenario_id} расчёт отсутствует")


class ConsultantServiceError(DomainError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
