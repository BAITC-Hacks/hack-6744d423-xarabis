import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from city_simulator.domain.chat import AnalysisBlock, ConsultantReport, ConsultantRequest
from city_simulator.domain.chat_ports import ConsultantGateway
from city_simulator.domain.exceptions import ConsultantServiceError
from city_simulator.infrastructure.database import Base, get_db_session
from city_simulator.infrastructure.models import ChatMessageModel
from city_simulator.main import app
from city_simulator.presentation.dependencies import get_consultant_gateway

EXAMPLE_DECISIONS = [
    {"measure_id": "M7", "district_id": "nura"},
    {"measure_id": "M8", "district_id": "nura"},
    {"measure_id": "M10", "district_id": "nura"},
    {"measure_id": "M12", "district_id": None},
    {"measure_id": "M5", "district_id": "saryarka"},
]


class StubConsultantGateway(ConsultantGateway):
    def __init__(self) -> None:
        self.requests: list[ConsultantRequest] = []

    async def generate(self, request: ConsultantRequest) -> ConsultantReport:
        self.requests.append(request)
        return ConsultantReport(
            answer="Проверенный ответ консультанта.",
            strengths=(AnalysisBlock("Сильная сторона", "Пояснение"),),
            risks=(),
            consequences=(AnalysisBlock("Последствие", "Транспорт улучшится"),),
            recommendations=(AnalysisBlock("Рекомендация", "Следующий шаг"),),
            follow_up_question="Продолжить анализ?",
        )


class FailingConsultantGateway(ConsultantGateway):
    async def generate(self, request: ConsultantRequest) -> ConsultantReport:
        raise ConsultantServiceError("ai_timeout")


@pytest.fixture
async def chat_client():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    gateway = StubConsultantGateway()

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_consultant_gateway] = lambda: gateway
    with TestClient(app) as client:
        yield client, gateway
    app.dependency_overrides.clear()
    await engine.dispose()


def test_chat_uses_trusted_scenario_context_and_persists_history(chat_client) -> None:
    client, gateway = chat_client
    scenario = client.post("/api/v1/scenarios").json()
    scenario_id = scenario["id"]

    first = client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages",
        json={"message": "  Что улучшить в плане?  "},
    )
    assert first.status_code == 200
    assert first.json()["answer"] == "Проверенный ответ консультанта."
    assert first.json()["consequences"] == [
        {"title": "Последствие", "explanation": "Транспорт улучшится"},
    ]
    assert gateway.requests[0].message == "Что улучшить в плане?"
    assert gateway.requests[0].history == ()
    assert gateway.requests[0].selected_measures == ()
    assert gateway.requests[0].budget_remaining == 100
    assert gateway.requests[0].simulation_result is None

    updated = client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 1, "decisions": EXAMPLE_DECISIONS},
    ).json()
    client.post(
        f"/api/v1/scenarios/{scenario_id}/calculate",
        json={"expected_version": updated["version"]},
    )
    second = client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages",
        json={"message": "Каким стал итог?"},
    )
    assert second.status_code == 200
    second_request = gateway.requests[1]
    assert len(second_request.history) == 2
    assert "Последствия:\nПоследствие: Транспорт улучшится" in second_request.history[1].content
    assert [item.role.value for item in second_request.history] == ["user", "assistant"]
    assert len(second_request.selected_measures) == 5
    assert second_request.budget_remaining == 5
    assert second_request.simulation_result is not None
    assert second_request.simulation_result.score_after == pytest.approx(56.54307)

    history = client.get(f"/api/v1/scenarios/{scenario_id}/chat/messages")
    assert history.status_code == 200
    assert [item["sequence"] for item in history.json()] == [1, 2, 3, 4]
    assert [item["role"] for item in history.json()] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert history.json()[1]["report"] == first.json()

    client.put(
        f"/api/v1/scenarios/{scenario_id}/decisions",
        json={"expected_version": 2, "decisions": []},
    )
    client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages",
        json={"message": "Расчёт ещё актуален?"},
    )
    assert gateway.requests[2].simulation_result is None


def test_failed_consultant_call_is_mapped_and_not_persisted(chat_client) -> None:
    client, _gateway = chat_client
    scenario_id = client.post("/api/v1/scenarios").json()["id"]
    app.dependency_overrides[get_consultant_gateway] = lambda: FailingConsultantGateway()

    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages",
        json={"message": "Ответь"},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_timeout"
    assert client.get(f"/api/v1/scenarios/{scenario_id}/chat/messages").json() == []


def test_chat_rejects_blank_message(chat_client) -> None:
    client, _gateway = chat_client
    scenario_id = client.post("/api/v1/scenarios").json()["id"]
    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages",
        json={"message": "   "},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


@pytest.mark.asyncio
async def test_chat_history_reads_legacy_report_without_inventing_consequences(chat_client) -> None:
    client, _gateway = chat_client
    scenario_id = client.post("/api/v1/scenarios").json()["id"]
    response = client.post(
        f"/api/v1/scenarios/{scenario_id}/chat/messages", json={"message": "Анализ"},
    )
    assert response.status_code == 200

    async for session in app.dependency_overrides[get_db_session]():
        stored = await session.scalar(
            select(ChatMessageModel).where(ChatMessageModel.role == "assistant")
        )
        assert stored.report["consequences"] == [
            {"title": "Последствие", "explanation": "Транспорт улучшится"},
        ]
        stored.report = {
            key: value for key, value in stored.report.items() if key != "consequences"
        }
        await session.commit()

    history = client.get(f"/api/v1/scenarios/{scenario_id}/chat/messages")
    assert history.status_code == 200
    report = history.json()[1]["report"]
    assert report["consequences"] == []
    assert report["answer"] == "Проверенный ответ консультанта."
    assert report["strengths"] == [{"title": "Сильная сторона", "explanation": "Пояснение"}]
