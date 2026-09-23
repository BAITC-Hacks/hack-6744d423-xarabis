"""Versioned, deterministic district sandbox; every request replays from scratch."""

from dataclasses import dataclass
from typing import Literal

from city_simulator.domain.sandbox import Improvement, SandboxValidationError

RULES_VERSION = "districts-v2"
CITY_NAME = "Новый Берег"
STARTING_BUDGET = 200
QUARTERLY_INCOME = 25
MAX_TURNS = 12
MAX_IMPROVEMENTS_PER_TURN = 3
CRITICAL_THRESHOLD = 40
TARGET_VALUE = 65
INDICATORS = ("transport", "air", "education")


@dataclass(frozen=True)
class DistrictDefinition:
    id: str
    name: str
    description: str
    values: tuple[int, int, int]


@dataclass(frozen=True)
class DistrictChoice:
    district_id: str
    improvement_id: str


@dataclass(frozen=True)
class DistrictState:
    id: str
    name: str
    description: str
    score: float
    values: dict[str, int]
    built: list[str]


@dataclass(frozen=True)
class DistrictChange:
    district_id: str
    indicator_id: str
    before: int
    after: int


@dataclass(frozen=True)
class DistrictSandboxResult:
    rules_version: str
    city_name: str
    quarter: int
    budget: int
    score: float
    districts: list[DistrictState]
    turns: list[list[DistrictChoice]]
    status: Literal["playing", "won", "finished"]
    last_changes: list[DistrictChange]
    last_income: int


# Names are borrowed from Astana; all indicators and descriptions are fictional.
INITIAL_DISTRICTS = (
    DistrictDefinition(
        "esil", "Есиль", "Учебный деловой район: нужны места в школах.", (70, 72, 54)
    ),
    DistrictDefinition(
        "almaty", "Алматы", "Учебный жилой район с перегруженными дорогами.", (28, 52, 48)
    ),
    DistrictDefinition(
        "saryarka", "Сарыарка", "Учебный промышленный район: воздух требует внимания.", (38, 24, 58)
    ),
    DistrictDefinition(
        "baikonur",
        "Байконур",
        "Учебный благоустроенный район с высокими показателями.",
        (76, 74, 72),
    ),
    DistrictDefinition(
        "nura", "Нура", "Учебный растущий район: нужны дороги и школы.", (26, 42, 26)
    ),
)
IMPROVEMENTS = (
    Improvement(
        "bus", "Автобусная линия", "Новый маршрут улучшит транспорт района.", 22, "transport", 24
    ),
    Improvement(
        "signals",
        "Умные светофоры",
        "Согласуем движение на перекрёстках района.",
        16,
        "transport",
        18,
    ),
    Improvement("park", "Городской парк", "Зелёная зона улучшит среду района.", 18, "air", 22),
    Improvement(
        "filter", "Фильтры на заводе", "Снизим промышленные выбросы в районе.", 26, "air", 30
    ),
    Improvement(
        "school", "Новая школа", "Добавим учебные места в выбранном районе.", 32, "education", 42
    ),
    Improvement(
        "repair", "Ремонт дорог", "Обновим дорожное покрытие в районе.", 30, "transport", 30
    ),
)


def simulate_district_sandbox(turns: list[list[DistrictChoice]]) -> DistrictSandboxResult:
    if len(turns) > MAX_TURNS:
        raise SandboxValidationError(f"Допустимо не более {MAX_TURNS} кварталов")

    improvements = {item.id: item for item in IMPROVEMENTS}
    values = {d.id: dict(zip(INDICATORS, d.values, strict=True)) for d in INITIAL_DISTRICTS}
    built: dict[str, list[str]] = {d.id: [] for d in INITIAL_DISTRICTS}
    budget = STARTING_BUDGET
    changes: list[DistrictChange] = []
    for quarter, turn in enumerate(turns, start=1):
        if len(turn) > MAX_IMPROVEMENTS_PER_TURN:
            raise SandboxValidationError(f"Квартал {quarter}: выберите не более трёх улучшений")
        if any(c.district_id not in values or c.improvement_id not in improvements for c in turn):
            raise SandboxValidationError(f"Квартал {quarter}: неизвестный район или улучшение")
        if len(set(turn)) != len(turn) or any(
            c.improvement_id in built[c.district_id] for c in turn
        ):
            raise SandboxValidationError(
                f"Квартал {quarter}: улучшение можно построить в районе только один раз"
            )
        cost = sum(improvements[c.improvement_id].cost for c in turn)
        if cost > budget:
            raise SandboxValidationError(
                f"Квартал {quarter}: стоимость {cost} превышает доступный бюджет {budget}"
            )
        before = {district_id: indicators.copy() for district_id, indicators in values.items()}
        for choice in turn:
            item = improvements[choice.improvement_id]
            district = values[choice.district_id]
            district[item.zone_id] = min(100, district[item.zone_id] + item.gain)
            built[choice.district_id].append(item.id)
        changes = [
            DistrictChange(district_id, indicator, before[district_id][indicator], value)
            for district_id, indicators in values.items()
            for indicator, value in indicators.items()
            if value != before[district_id][indicator]
        ]
        budget = budget - cost + QUARTERLY_INCOME

    status: Literal["playing", "won", "finished"] = "playing"
    if all(
        value >= TARGET_VALUE for indicators in values.values() for value in indicators.values()
    ):
        status = "won"
    elif len(turns) == MAX_TURNS:
        status = "finished"
    districts = [
        DistrictState(
            d.id,
            d.name,
            d.description,
            round(sum(values[d.id].values()) / 3, 1),
            values[d.id],
            built[d.id],
        )
        for d in INITIAL_DISTRICTS
    ]
    return DistrictSandboxResult(
        rules_version=RULES_VERSION,
        city_name=CITY_NAME,
        quarter=len(turns) + 1,
        budget=budget,
        score=round(sum(sum(indicators.values()) / 3 for indicators in values.values()) / 5, 1),
        districts=districts,
        turns=[list(turn) for turn in turns],
        status=status,
        last_changes=changes,
        last_income=QUARTERLY_INCOME if turns else 0,
    )
