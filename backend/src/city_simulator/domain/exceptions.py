class DomainError(Exception):
    """Base error for an expected business-rule violation."""


class ScenarioValidationError(DomainError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class DatasetConfigurationError(DomainError):
    """Raised when the versioned simulation dataset is internally inconsistent."""
