class DomainError(Exception):
    """Base error for an expected business-rule violation."""


class ScenarioValidationError(DomainError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class DatasetConfigurationError(DomainError):
    """Raised when the versioned simulation dataset is internally inconsistent."""


class ScenarioNotFoundError(DomainError):
    def __init__(self, scenario_id: object) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"Сценарий {scenario_id} не найден")


class ScenarioVersionConflictError(DomainError):
    def __init__(self, scenario_id: object) -> None:
        self.scenario_id = scenario_id
        super().__init__("Сценарий уже изменён другим запросом; обновите данные и повторите")


class SimulationResultNotFoundError(DomainError):
    def __init__(self, scenario_id: object) -> None:
        self.scenario_id = scenario_id
        super().__init__(f"Для текущей версии сценария {scenario_id} расчёт отсутствует")
