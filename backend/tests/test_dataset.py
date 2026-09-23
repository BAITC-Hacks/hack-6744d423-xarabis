from pathlib import Path

import pytest

from city_simulator.domain.enums import ConflictScope, Direction, IndicatorCode, MeasureScope
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


def test_dataset_rules_and_district_rows_match_source_document(dataset) -> None:
    rules = dataset.rules
    assert (
        rules.budget,
        rules.horizon_quarters,
        rules.required_decisions,
        rules.max_measures_per_direction,
        rules.critical_threshold,
        rules.city_average_weight,
        rules.weakest_district_weight,
        rules.critical_penalty,
    ) == (100, 8, 5, 2, 40, 0.7, 0.3, 1.0)
    assert {code.value: value for code, value in rules.indicator_weights.items()} == {
        "T1": 0.10,
        "T2": 0.10,
        "E1": 0.09,
        "E2": 0.11,
        "S1": 0.11,
        "S2": 0.11,
        "B1": 0.09,
        "B2": 0.09,
        "C1": 0.10,
        "C2": 0.10,
    }
    assert {
        indicator.id.value: (indicator.direction, indicator.name, indicator.scale_description)
        for indicator in dataset.indicators
    } == {
        "T1": (
            Direction.TRANSPORT,
            "Разгрузка дорог",
            "100 = нет пробок в час пик, 0 = стоит всё",
        ),
        "T2": (
            Direction.TRANSPORT,
            "Доступность общественного транспорта",
            "100 = все жители в 500 м от остановки с интервалом ≤10 мин",
        ),
        "E1": (Direction.ECOLOGY, "Озеленение", "100 = ≥20 м² зелени на жителя"),
        "E2": (
            Direction.ECOLOGY,
            "Качество воздуха",
            "100 = зимой AQI ≤50, 0 = хронический смог",
        ),
        "S1": (
            Direction.SOCIAL,
            "Школы и детсады",
            "100 = 100% нормативной потребности, без 2-й смены",
        ),
        "S2": (
            Direction.SOCIAL,
            "Поликлиники и первичная медпомощь",
            "100 = норматив на жителя выполнен полностью",
        ),
        "B1": (
            Direction.SAFETY,
            "Безопасность улиц",
            "100 = освещение и камеры везде, минимум происшествий",
        ),
        "B2": (
            Direction.SAFETY,
            "Безопасность дорожного движения",
            "100 = минимум ДТП с пострадавшими",
        ),
        "C1": (
            Direction.SERVICES,
            "Надёжность ЖКХ",
            "100 = нет аварий отопления/воды за год",
        ),
        "C2": (
            Direction.SERVICES,
            "Скорость решения обращений жителей",
            "100 = все обращения закрыты в срок",
        ),
    }
    assert {
        district.id: (
            district.name,
            district.population_share,
            {code.value: value for code, value in district.indicators.items()},
        )
        for district in dataset.districts
    } == {
        "esil": (
            "Есиль",
            0.27,
            {
                "T1": 45,
                "T2": 62,
                "E1": 68,
                "E2": 72,
                "S1": 48,
                "S2": 55,
                "B1": 78,
                "B2": 60,
                "C1": 75,
                "C2": 70,
            },
        ),
        "almaty": (
            "Алматы",
            0.24,
            {
                "T1": 40,
                "T2": 75,
                "E1": 50,
                "E2": 55,
                "S1": 60,
                "S2": 65,
                "B1": 62,
                "B2": 52,
                "C1": 50,
                "C2": 60,
            },
        ),
        "saryarka": (
            "Сарыарка",
            0.20,
            {
                "T1": 50,
                "T2": 70,
                "E1": 42,
                "E2": 40,
                "S1": 62,
                "S2": 68,
                "B1": 58,
                "B2": 55,
                "C1": 45,
                "C2": 55,
            },
        ),
        "baikonur": (
            "Байконур",
            0.13,
            {
                "T1": 52,
                "T2": 68,
                "E1": 55,
                "E2": 50,
                "S1": 58,
                "S2": 60,
                "B1": 52,
                "B2": 58,
                "C1": 55,
                "C2": 58,
            },
        ),
        "nura": (
            "Нура",
            0.16,
            {
                "T1": 55,
                "T2": 40,
                "E1": 45,
                "E2": 65,
                "S1": 38,
                "S2": 35,
                "B1": 55,
                "B2": 50,
                "C1": 60,
                "C2": 50,
            },
        ),
    }
    assert {district.id: district.profile for district in dataset.districts} == {
        "esil": "Богатый, но с пробками на мостах и переполненными школами.",
        "almaty": "Старый ЖКХ и пробки.",
        "saryarka": "Смог от частного сектора, слабое озеленение.",
        "baikonur": "Середняк без ярких перекосов.",
        "nura": "Главный «аутсайдер» по соцсфере и транспорту.",
    }


def test_measures_synergies_and_conflicts_match_source_document(dataset) -> None:
    assert {
        measure.id: (
            measure.direction,
            measure.name,
            measure.scope,
            measure.cost,
            measure.lag_quarters,
            {code.value: value for code, value in measure.effects.items()},
        )
        for measure in dataset.measures
    } == {
        "M1": (
            Direction.TRANSPORT,
            "Выделенные полосы для автобусов",
            MeasureScope.DISTRICT,
            18,
            2,
            {"T1": 6, "T2": 9},
        ),
        "M2": (
            Direction.TRANSPORT,
            "Умные светофоры (адаптивное управление)",
            MeasureScope.CITY,
            22,
            2,
            {"T1": 4, "B2": 3},
        ),
        "M3": (
            Direction.TRANSPORT,
            "Линия ЛРТ / расширение",
            MeasureScope.DISTRICT,
            30,
            4,
            {"T1": 16, "T2": 20, "E2": 4},
        ),
        "M4": (
            Direction.ECOLOGY,
            "Парк / сквер",
            MeasureScope.DISTRICT,
            15,
            2,
            {"E1": 12, "E2": 3, "B1": 2},
        ),
        "M5": (
            Direction.ECOLOGY,
            "Перевод частного сектора на чистое топливо",
            MeasureScope.DISTRICT,
            25,
            3,
            {"E2": 14, "C1": 4},
        ),
        "M6": (
            Direction.ECOLOGY,
            "Городская программа озеленения и ветрозащитных полос",
            MeasureScope.CITY,
            20,
            4,
            {"E1": 5, "E2": 3},
        ),
        "M7": (
            Direction.SOCIAL,
            "Школа + детсад (модульное строительство)",
            MeasureScope.DISTRICT,
            24,
            3,
            {"S1": 16},
        ),
        "M8": (
            Direction.SOCIAL,
            "Центр семейного здоровья / поликлиника",
            MeasureScope.DISTRICT,
            20,
            3,
            {"S2": 14},
        ),
        "M9": (
            Direction.SOCIAL,
            "Дворовые спорт-хабы",
            MeasureScope.DISTRICT,
            10,
            1,
            {"S1": 3, "S2": 3, "B1": 3},
        ),
        "M10": (
            Direction.SAFETY,
            "Освещение и камеры (расширение Safe City)",
            MeasureScope.DISTRICT,
            12,
            1,
            {"B1": 12, "B2": 2},
        ),
        "M11": (
            Direction.SAFETY,
            "Безопасные переходы и школьные зоны",
            MeasureScope.DISTRICT,
            10,
            1,
            {"B2": 12, "T1": -2},
        ),
        "M12": (
            Direction.SERVICES,
            "Единая цифровая платформа обращений",
            MeasureScope.CITY,
            14,
            1,
            {"C2": 5},
        ),
        "M13": (
            Direction.SERVICES,
            "Модернизация тепло- и водосетей",
            MeasureScope.DISTRICT,
            28,
            4,
            {"C1": 18, "E2": 2},
        ),
        "M14": (
            Direction.SERVICES,
            "Аварийные бригады ЖКХ + раннее оповещение",
            MeasureScope.CITY,
            16,
            1,
            {"C1": 5, "C2": 2},
        ),
    }
    assert [
        (item.measure_ids, item.target_measure_id, item.indicator_id.value, item.delta)
        for item in dataset.synergies
    ] == [
        (("M1", "M2"), "M1", "T1", 2),
        (("M10", "M12"), "M10", "B1", 2),
        (("M5", "M6"), "M5", "E2", 2),
    ]
    assert [(item.measure_ids, item.scope) for item in dataset.incompatibilities] == [
        (("M1", "M3"), ConflictScope.GLOBAL),
        (("M4", "M7"), ConflictScope.SAME_DISTRICT),
        (("M5", "M13"), ConflictScope.SAME_DISTRICT),
    ]


def test_invalid_dataset_fails_fast() -> None:
    invalid_path = Path(__file__).parent / "fixtures" / "invalid_dataset.json"
    with pytest.raises(DatasetConfigurationError):
        VersionedJsonCityDataRepository(invalid_path).get_dataset()
