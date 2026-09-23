from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from city_simulator.domain.chat import AnalysisBlock, ChatMessage, ConsultantReport
from city_simulator.domain.chat_ports import ChatRepository
from city_simulator.domain.enums import ChatRole
from city_simulator.infrastructure.models import (
    ChatConversationModel,
    ChatMessageModel,
    ScenarioModel,
)


def report_to_payload(report: ConsultantReport) -> dict[str, Any]:
    return {
        "answer": report.answer,
        "strengths": [
            {"title": item.title, "explanation": item.explanation}
            for item in report.strengths
        ],
        "risks": [
            {"title": item.title, "explanation": item.explanation} for item in report.risks
        ],
        "recommendations": [
            {"title": item.title, "explanation": item.explanation}
            for item in report.recommendations
        ],
        "consequences": [
            {"title": item.title, "explanation": item.explanation}
            for item in report.consequences
        ],
        "follow_up_question": report.follow_up_question,
    }


def payload_to_report(payload: dict[str, Any]) -> ConsultantReport:
    def blocks(key: str) -> tuple[AnalysisBlock, ...]:
        return tuple(
            AnalysisBlock(title=item["title"], explanation=item["explanation"])
            for item in payload[key]
        )

    return ConsultantReport(
        answer=payload["answer"],
        strengths=blocks("strengths"),
        risks=blocks("risks"),
        consequences=blocks("consequences") if "consequences" in payload else (),
        recommendations=blocks("recommendations"),
        follow_up_question=payload["follow_up_question"],
    )


class SqlAlchemyChatRepository(ChatRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_messages(
        self,
        scenario_id: UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[ChatMessage]:
        statement = (
            select(ChatMessageModel)
            .join(ChatConversationModel)
            .where(ChatConversationModel.scenario_id == scenario_id)
        )
        if limit is None:
            statement = statement.order_by(ChatMessageModel.sequence.asc())
        else:
            statement = statement.order_by(ChatMessageModel.sequence.desc()).limit(limit)
        models = list((await self._session.scalars(statement)).all())
        if limit is not None:
            models.reverse()
        return tuple(self._to_message(model, scenario_id) for model in models)

    async def append_exchange(
        self,
        scenario_id: UUID,
        *,
        user_content: str,
        assistant_content: str,
        report: ConsultantReport,
    ) -> tuple[ChatMessage, ChatMessage]:
        await self._session.scalar(
            select(ScenarioModel.id)
            .where(ScenarioModel.id == scenario_id)
            .with_for_update()
        )
        conversation = await self._session.scalar(
            select(ChatConversationModel)
            .where(ChatConversationModel.scenario_id == scenario_id)
            .with_for_update()
        )
        if conversation is None:
            conversation = ChatConversationModel(scenario_id=scenario_id)
            self._session.add(conversation)
            await self._session.flush()

        user_model = ChatMessageModel(
            conversation_id=conversation.id,
            sequence=conversation.next_sequence,
            role=ChatRole.USER.value,
            content=user_content,
            report=None,
        )
        assistant_model = ChatMessageModel(
            conversation_id=conversation.id,
            sequence=conversation.next_sequence + 1,
            role=ChatRole.ASSISTANT.value,
            content=assistant_content,
            report=report_to_payload(report),
        )
        conversation.next_sequence += 2
        self._session.add_all((user_model, assistant_model))
        await self._session.commit()
        await self._session.refresh(user_model)
        await self._session.refresh(assistant_model)
        return (
            self._to_message(user_model, scenario_id),
            self._to_message(assistant_model, scenario_id),
        )

    @staticmethod
    def _to_message(model: ChatMessageModel, scenario_id: UUID) -> ChatMessage:
        return ChatMessage(
            id=model.id,
            scenario_id=scenario_id,
            sequence=model.sequence,
            role=ChatRole(model.role),
            content=model.content,
            report=payload_to_report(model.report) if model.report else None,
            created_at=model.created_at,
        )
