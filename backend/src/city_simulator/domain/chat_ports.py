from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from city_simulator.domain.chat import (
    ChatMessage,
    ConsultantReport,
    ConsultantRequest,
)


class ChatRepository(ABC):
    @abstractmethod
    async def list_messages(
        self,
        scenario_id: UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[ChatMessage]: ...

    @abstractmethod
    async def append_exchange(
        self,
        scenario_id: UUID,
        *,
        user_content: str,
        assistant_content: str,
        report: ConsultantReport,
    ) -> tuple[ChatMessage, ChatMessage]: ...


class ConsultantGateway(ABC):
    @abstractmethod
    async def generate(self, request: ConsultantRequest) -> ConsultantReport: ...
