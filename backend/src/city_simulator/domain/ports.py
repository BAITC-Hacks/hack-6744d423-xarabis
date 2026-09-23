from abc import ABC, abstractmethod
from collections.abc import Sequence

from city_simulator.domain.entities import (
    Decision,
    District,
    Measure,
    ScenarioAnalysis,
    ScenarioResult,
)


class CityDataRepository(ABC):
    @abstractmethod
    def list_districts(self) -> Sequence[District]: ...

    @abstractmethod
    def list_measures(self) -> Sequence[Measure]: ...

    @abstractmethod
    def get_district(self, district_id: str) -> District | None: ...

    @abstractmethod
    def get_measure(self, measure_id: str) -> Measure | None: ...


class ScenarioAnalyst(ABC):
    @abstractmethod
    def analyze(
        self,
        result: ScenarioResult,
        decisions: Sequence[Decision],
        measures: Sequence[Measure],
    ) -> ScenarioAnalysis: ...
