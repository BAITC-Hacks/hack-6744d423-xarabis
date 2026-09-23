"""Deterministic, stateless rules for the fictional training city."""

from dataclasses import dataclass, replace
from typing import Literal

CITY_NAME = "Новый Берег"
STARTING_BUDGET = 100
QUARTERLY_INCOME = 12
MAX_TURNS = 12
CRITICAL_THRESHOLD = 40
TARGET_VALUE = 65


class SandboxValidationError(ValueError):
    """The submitted history cannot be played under the sandbox rules."""


@dataclass(frozen=True)
class SandboxZone:
    id: str
    name: str
    value: int
    description: str


@dataclass(frozen=True)
class Improvement:
    id: str
    name: str
    description: str
    cost: int
    zone_id: str
    gain: int


@dataclass(frozen=True)
class ZoneChange:
    zone_id: str
    before: int
    after: int


@dataclass(frozen=True)
class SandboxResult:
    city_name: str
    quarter: int
    budget: int
    score: float
    zones: list[SandboxZone]
    built: list[str]
    turns: list[list[str]]
    status: Literal["playing", "won", "finished"]
    last_changes: list[ZoneChange]
    last_income: int


INITIAL_ZONES = (
    SandboxZone(
        "transport", "Центральный проспект", 28, "Удобство движения и общественного транспорта"
    ),
    SandboxZone("air", "Заводской квартал", 34, "Качество воздуха и городской среды"),
    SandboxZone("education", "Северный район", 26, "Доступность мест в школах"),
)
IMPROVEMENTS = (
    Improvement(
        "bus", "Автобусная линия", "Новый маршрут разгрузит проспект.", 22, "transport", 24
    ),
    Improvement(
        "signals", "Умные светофоры", "Согласуем движение на перекрёстках.", 16, "transport", 18
    ),
    Improvement("park", "Городской парк", "Зелёная зона улучшит городскую среду.", 18, "air", 22),
    Improvement("filter", "Фильтры на заводе", "Снизим промышленные выбросы.", 26, "air", 30),
    Improvement(
        "school", "Новая школа", "Добавим учебные места в северном районе.", 32, "education", 42
    ),
)


def simulate_sandbox(turns: list[list[str]]) -> SandboxResult:
    if len(turns) > MAX_TURNS:
        raise SandboxValidationError(f"Допустимо не более {MAX_TURNS} кварталов")

    improvements = {item.id: item for item in IMPROVEMENTS}
    zones = {zone.id: zone for zone in INITIAL_ZONES}
    budget = STARTING_BUDGET
    built: list[str] = []
    changes: list[ZoneChange] = []
    for quarter, turn in enumerate(turns, start=1):
        if len(turn) > 3:
            raise SandboxValidationError(f"Квартал {quarter}: выберите не более трёх улучшений")
        if len(set(turn)) != len(turn) or any(item in built for item in turn):
            raise SandboxValidationError(
                f"Квартал {quarter}: улучшение можно построить только один раз"
            )
        if any(item not in improvements for item in turn):
            raise SandboxValidationError(f"Квартал {quarter}: неизвестное улучшение")
        cost = sum(improvements[item].cost for item in turn)
        if cost > budget:
            raise SandboxValidationError(
                f"Квартал {quarter}: стоимость {cost} превышает доступный бюджет {budget}"
            )
        before = {zone_id: zone.value for zone_id, zone in zones.items()}
        for item_id in turn:
            item = improvements[item_id]
            zone = zones[item.zone_id]
            zones[item.zone_id] = replace(zone, value=min(100, zone.value + item.gain))
        changes = [
            ZoneChange(zone.id, before[zone.id], zone.value)
            for zone in zones.values()
            if zone.value != before[zone.id]
        ]
        built.extend(turn)
        budget = budget - cost + QUARTERLY_INCOME

    status: Literal["playing", "won", "finished"] = "playing"
    if all(zone.value >= TARGET_VALUE for zone in zones.values()):
        status = "won"
    elif len(turns) == MAX_TURNS:
        status = "finished"
    return SandboxResult(
        city_name=CITY_NAME,
        quarter=len(turns) + 1,
        budget=budget,
        score=round(sum(zone.value for zone in zones.values()) / len(zones), 1),
        zones=list(zones.values()),
        built=built,
        turns=[list(turn) for turn in turns],
        status=status,
        last_changes=changes,
        last_income=QUARTERLY_INCOME if turns else 0,
    )
