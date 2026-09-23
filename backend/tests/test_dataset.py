from pathlib import Path

import pytest

from city_simulator.domain.enums import IndicatorCode
from city_simulator.domain.exceptions import DatasetConfigurationError
from city_simulator.infrastructure.repositories import VersionedJsonCityDataRepository


def test_versioned_dataset_is_complete(dataset) -> None:
    assert dataset.dataset_version == "1.0"
    assert dataset.formula_version == "1.0"
    assert len(dataset.indicators) == 10
    assert len(dataset.districts) == 5
    assert len(dataset.measures) == 14
    assert set(dataset.rules.indicator_weights) == set(IndicatorCode)
    assert sum(item.population_share for item in dataset.districts) == pytest.approx(1.0)
    assert sum(dataset.rules.indicator_weights.values()) == pytest.approx(1.0)
    assert dataset.get_district("esil") is not None
    assert dataset.get_district("yesil") is None


def test_invalid_dataset_fails_fast() -> None:
    invalid_path = Path(__file__).parent / "fixtures" / "invalid_dataset.json"
    with pytest.raises(DatasetConfigurationError):
        VersionedJsonCityDataRepository(invalid_path).get_dataset()
