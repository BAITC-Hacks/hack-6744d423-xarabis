import pytest

from city_simulator.domain.entities import Decision, SimulationDataset
from city_simulator.infrastructure.repositories import VersionedJsonCityDataRepository


@pytest.fixture(scope="session")
def dataset() -> SimulationDataset:
    return VersionedJsonCityDataRepository().get_dataset()


@pytest.fixture
def example_decisions() -> tuple[Decision, ...]:
    return (
        Decision("M7", "nura"),
        Decision("M8", "nura"),
        Decision("M10", "nura"),
        Decision("M12"),
        Decision("M5", "saryarka"),
    )
