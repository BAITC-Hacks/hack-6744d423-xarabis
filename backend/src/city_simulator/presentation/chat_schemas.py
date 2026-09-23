from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, StringConstraints

from city_simulator.domain.enums import ChatRole
from city_simulator.presentation.schemas import StrictModel


class SendChatMessageRequest(StrictModel):
    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
    ]


class AnalysisBlockResponse(StrictModel):
    title: str
    explanation: str


class ConsultantReportResponse(StrictModel):
    answer: str
    strengths: list[AnalysisBlockResponse]
    risks: list[AnalysisBlockResponse]
    consequences: list[AnalysisBlockResponse] = Field(max_length=5)
    recommendations: list[AnalysisBlockResponse]
    follow_up_question: str | None


class ChatMessageResponse(StrictModel):
    id: UUID
    scenario_id: UUID
    sequence: int
    role: ChatRole
    content: str
    report: ConsultantReportResponse | None
    created_at: datetime
