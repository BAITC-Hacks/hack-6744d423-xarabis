from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from city_simulator.application.chat import ListChatMessagesUseCase, SendChatMessageUseCase
from city_simulator.domain.chat import ChatMessage, ConsultantReport
from city_simulator.presentation.chat_schemas import (
    AnalysisBlockResponse,
    ChatMessageResponse,
    ConsultantReportResponse,
    SendChatMessageRequest,
)
from city_simulator.presentation.dependencies import (
    get_list_chat_messages_use_case,
    get_send_chat_message_use_case,
)
from city_simulator.presentation.schemas import ErrorResponse

router = APIRouter(prefix="/scenarios", tags=["consultant"])

CHAT_ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Сценарий не найден"},
    422: {"model": ErrorResponse, "description": "Невалидный запрос"},
    502: {"model": ErrorResponse, "description": "Некорректный ответ AI"},
    503: {"model": ErrorResponse, "description": "AI временно недоступен"},
    504: {"model": ErrorResponse, "description": "Таймаут AI"},
}


def _to_report_response(report: ConsultantReport) -> ConsultantReportResponse:
    def blocks(items):
        return [
            AnalysisBlockResponse(title=item.title, explanation=item.explanation)
            for item in items
        ]

    return ConsultantReportResponse(
        answer=report.answer,
        strengths=blocks(report.strengths),
        risks=blocks(report.risks),
        consequences=blocks(report.consequences),
        recommendations=blocks(report.recommendations),
        follow_up_question=report.follow_up_question,
    )


def _to_message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        scenario_id=message.scenario_id,
        sequence=message.sequence,
        role=message.role,
        content=message.content,
        report=_to_report_response(message.report) if message.report else None,
        created_at=message.created_at,
    )


@router.post(
    "/{scenario_id}/chat/messages",
    response_model=ConsultantReportResponse,
    responses=CHAT_ERROR_RESPONSES,
)
async def send_chat_message(
    scenario_id: UUID,
    payload: SendChatMessageRequest,
    use_case: Annotated[
        SendChatMessageUseCase,
        Depends(get_send_chat_message_use_case),
    ],
) -> ConsultantReportResponse:
    return _to_report_response(
        await use_case.execute(scenario_id, message=payload.message)
    )


@router.get(
    "/{scenario_id}/chat/messages",
    response_model=list[ChatMessageResponse],
    responses=CHAT_ERROR_RESPONSES,
)
async def list_chat_messages(
    scenario_id: UUID,
    use_case: Annotated[
        ListChatMessagesUseCase,
        Depends(get_list_chat_messages_use_case),
    ],
) -> list[ChatMessageResponse]:
    return [
        _to_message_response(item) for item in await use_case.execute(scenario_id)
    ]
