from types import MappingProxyType

from city_simulator.domain.entities import District, Measure
from city_simulator.domain.enums import Direction, MeasureScope
from city_simulator.domain.enums import IndicatorCode as I
from city_simulator.domain.ports import CityDataRepository


def _values(**values: float) -> MappingProxyType:
    return MappingProxyType({I(code): value for code, value in values.items()})


DISTRICTS: tuple[District, ...] = (
    District(
        "yesil",
        "Есиль",
        0.27,
        _values(T1=45, T2=62, E1=68, E2=72, S1=48, S2=55, B1=78, B2=60, C1=75, C2=70),
        "Богатый район, но с пробками на мостах и переполненными школами.",
    ),
    District(
        "almaty",
        "Алматы",
        0.24,
        _values(T1=40, T2=75, E1=50, E2=55, S1=60, S2=65, B1=62, B2=52, C1=50, C2=60),
        "Старый ЖКХ и пробки.",
    ),
    District(
        "saryarka",
        "Сарыарка",
        0.20,
        _values(T1=50, T2=70, E1=42, E2=40, S1=62, S2=68, B1=58, B2=55, C1=45, C2=55),
        "Смог от частного сектора и слабое озеленение.",
    ),
    District(
        "baikonur",
        "Байконур",
        0.13,
        _values(T1=52, T2=68, E1=55, E2=50, S1=58, S2=60, B1=52, B2=58, C1=55, C2=58),
        "Средний район без ярких перекосов.",
    ),
    District(
        "nura",
        "Нура",
        0.16,
        _values(T1=55, T2=40, E1=45, E2=65, S1=38, S2=35, B1=55, B2=50, C1=60, C2=50),
        "Главный аутсайдер по социальной сфере и транспорту.",
    ),
)


MEASURES: tuple[Measure, ...] = (
    Measure(
        "M1",
        Direction.TRANSPORT,
        "Выделенные полосы для автобусов",
        MeasureScope.DISTRICT,
        18,
        2,
        _values(T1=6, T2=9),
    ),
    Measure(
        "M2", Direction.TRANSPORT, "Умные светофоры", MeasureScope.CITY, 22, 2, _values(T1=4, B2=3)
    ),
    Measure(
        "M3",
        Direction.TRANSPORT,
        "Линия ЛРТ / расширение",
        MeasureScope.DISTRICT,
        30,
        4,
        _values(T1=16, T2=20, E2=4),
    ),
    Measure(
        "M4",
        Direction.ECOLOGY,
        "Парк / сквер",
        MeasureScope.DISTRICT,
        15,
        2,
        _values(E1=12, E2=3, B1=2),
    ),
    Measure(
        "M5",
        Direction.ECOLOGY,
        "Перевод частного сектора на чистое топливо",
        MeasureScope.DISTRICT,
        25,
        3,
        _values(E2=14, C1=4),
    ),
    Measure(
        "M6",
        Direction.ECOLOGY,
        "Городская программа озеленения и ветрозащитных полос",
        MeasureScope.CITY,
        20,
        4,
        _values(E1=5, E2=3),
    ),
    Measure("M7", Direction.SOCIAL, "Школа + детсад", MeasureScope.DISTRICT, 24, 3, _values(S1=16)),
    Measure(
        "M8",
        Direction.SOCIAL,
        "Центр семейного здоровья / поликлиника",
        MeasureScope.DISTRICT,
        20,
        3,
        _values(S2=14),
    ),
    Measure(
        "M9",
        Direction.SOCIAL,
        "Дворовые спорт-хабы",
        MeasureScope.DISTRICT,
        10,
        1,
        _values(S1=3, S2=3, B1=3),
    ),
    Measure(
        "M10",
        Direction.SAFETY,
        "Освещение и камеры Safe City",
        MeasureScope.DISTRICT,
        12,
        1,
        _values(B1=12, B2=2),
    ),
    Measure(
        "M11",
        Direction.SAFETY,
        "Безопасные переходы и школьные зоны",
        MeasureScope.DISTRICT,
        10,
        1,
        _values(B2=12, T1=-2),
    ),
    Measure(
        "M12",
        Direction.SERVICES,
        "Единая цифровая платформа обращений",
        MeasureScope.CITY,
        14,
        1,
        _values(C2=5),
    ),
    Measure(
        "M13",
        Direction.SERVICES,
        "Модернизация тепло- и водосетей",
        MeasureScope.DISTRICT,
        28,
        4,
        _values(C1=18, E2=2),
    ),
    Measure(
        "M14",
        Direction.SERVICES,
        "Аварийные бригады ЖКХ + раннее оповещение",
        MeasureScope.CITY,
        16,
        1,
        _values(C1=5, C2=2),
    ),
)


class InMemoryCityDataRepository(CityDataRepository):
    def list_districts(self) -> tuple[District, ...]:
        return DISTRICTS

    def list_measures(self) -> tuple[Measure, ...]:
        return MEASURES

    def get_district(self, district_id: str) -> District | None:
        return next((item for item in DISTRICTS if item.id == district_id), None)

    def get_measure(self, measure_id: str) -> Measure | None:
        return next((item for item in MEASURES if item.id == measure_id.upper()), None)
