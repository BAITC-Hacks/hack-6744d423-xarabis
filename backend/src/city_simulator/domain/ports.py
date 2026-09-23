from abc import ABC, abstractmethod

from city_simulator.domain.entities import SimulationDataset


class CityDataRepository(ABC):
    @abstractmethod
    def get_dataset(self) -> SimulationDataset: ...
