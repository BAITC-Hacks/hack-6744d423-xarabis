from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from city_simulator.domain.entities import Decision, ScenarioResult
from city_simulator.domain.enums import ChatRole


@dataclass(frozen=True, slots=True)
class AnalysisBlock:
    title: str
    explanation: str


@dataclass(frozen=True, slots=True)
class ConsultantReport:
    answer: str
    strengths: tuple[AnalysisBlock, ...]
    risks: tuple[AnalysisBlock, ...]
    recommendations: tuple[AnalysisBlock, ...]
    follow_up_question: str | None


@dataclass(frozen=True, slots=True)
class ChatMessage:
    id: UUID
    scenario_id: UUID
    sequence: int
    role: ChatRole
    content: str
    report: ConsultantReport | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConsultantHistoryMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class ConsultantRequest:
    message: str
    history: tuple[ConsultantHistoryMessage, ...]
    selected_measures: tuple[Decision, ...]
    budget_remaining: int
    simulation_result: ScenarioResult | None
