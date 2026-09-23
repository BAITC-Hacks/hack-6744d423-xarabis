from collections.abc import Sequence
from uuid import UUID

from city_simulator.domain.chat import (
    ChatMessage,
    ConsultantHistoryMessage,
    ConsultantReport,
    ConsultantRequest,
)
from city_simulator.domain.chat_ports import ChatRepository, ConsultantGateway
from city_simulator.domain.exceptions import ScenarioNotFoundError
from city_simulator.domain.ports import CityDataRepository
from city_simulator.domain.scenario_ports import ScenarioRepository


def report_to_history(report: ConsultantReport) -> str:
    sections = [report.answer]
    for heading, blocks in (
        ("Сильные стороны", report.strengths),
        ("Риски", report.risks),
        ("Рекомендации", report.recommendations),
    ):
        if blocks:
            sections.append(
                f"{heading}:\n"
                + "\n".join(f"{item.title}: {item.explanation}" for item in blocks)
            )
    if report.follow_up_question:
        sections.append(report.follow_up_question)
    return "\n\n".join(sections)[:4000].rstrip()


class SendChatMessageUseCase:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        chats: ChatRepository,
        consultant: ConsultantGateway,
        city_data: CityDataRepository,
    ) -> None:
        self._scenarios = scenarios
        self._chats = chats
        self._consultant = consultant
        self._city_data = city_data

    async def execute(self, scenario_id: UUID, *, message: str) -> ConsultantReport:
        scenario = await self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(scenario_id)

        history = await self._chats.list_messages(scenario_id, limit=20)
        current_result = await self._scenarios.get_current_result(scenario_id)
        dataset = self._city_data.get_dataset()
        measure_by_id = {item.id: item for item in dataset.measures}
        total_cost = sum(measure_by_id[item.measure_id].cost for item in scenario.decisions)
        request = ConsultantRequest(
            message=message,
            history=tuple(
                ConsultantHistoryMessage(role=item.role, content=item.content)
                for item in history
            ),
            selected_measures=scenario.decisions,
            budget_remaining=scenario.budget_limit - total_cost,
            simulation_result=current_result.result if current_result else None,
        )
        report = await self._consultant.generate(request)
        await self._chats.append_exchange(
            scenario_id,
            user_content=message,
            assistant_content=report_to_history(report),
            report=report,
        )
        return report


class ListChatMessagesUseCase:
    def __init__(
        self,
        scenarios: ScenarioRepository,
        chats: ChatRepository,
    ) -> None:
        self._scenarios = scenarios
        self._chats = chats

    async def execute(self, scenario_id: UUID) -> Sequence[ChatMessage]:
        if await self._scenarios.get(scenario_id) is None:
            raise ScenarioNotFoundError(scenario_id)
        return await self._chats.list_messages(scenario_id)
