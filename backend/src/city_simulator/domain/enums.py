from enum import StrEnum


class Direction(StrEnum):
    TRANSPORT = "transport"
    ECOLOGY = "ecology"
    SOCIAL = "social"
    SAFETY = "safety"
    SERVICES = "services"


class MeasureScope(StrEnum):
    DISTRICT = "district"
    CITY = "city"


class ConflictScope(StrEnum):
    GLOBAL = "global"
    SAME_DISTRICT = "same_district"


class EffectKind(StrEnum):
    DIRECT = "direct"
    SYNERGY = "synergy"


class ScenarioStatus(StrEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    COMPLETED = "completed"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class IndicatorCode(StrEnum):
    T1 = "T1"
    T2 = "T2"
    E1 = "E1"
    E2 = "E2"
    S1 = "S1"
    S2 = "S2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"
