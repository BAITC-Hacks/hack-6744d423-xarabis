from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from city_simulator.presentation.middleware import (
    ChatRateLimitMiddleware,
    RequestContextMiddleware,
)


def test_chat_rate_limit_is_scoped_by_scenario_and_returns_retry_metadata() -> None:
    application = FastAPI()
    application.add_middleware(ChatRateLimitMiddleware, requests_per_minute=2)
    application.add_middleware(
        RequestContextMiddleware,
        max_request_body_bytes=1024,
        debug=False,
    )

    @application.post("/api/v1/scenarios/{scenario_id}/chat/messages")
    async def chat(scenario_id: str):
        return {"scenario_id": scenario_id}

    with TestClient(application) as client:
        assert client.post("/api/v1/scenarios/first/chat/messages").status_code == 200
        assert client.post("/api/v1/scenarios/first/chat/messages").status_code == 200
        limited = client.post("/api/v1/scenarios/first/chat/messages")
        other_scenario = client.post("/api/v1/scenarios/second/chat/messages")

    assert limited.status_code == 429
    assert limited.headers["retry-after"]
    assert limited.json()["error"]["code"] == "chat_rate_limit_exceeded"
    assert limited.json()["error"]["request_id"] == limited.headers["x-request-id"]
    assert other_scenario.status_code == 200


def test_body_limit_applies_without_content_length() -> None:
    application = FastAPI()
    application.add_middleware(
        RequestContextMiddleware,
        max_request_body_bytes=10,
        debug=False,
    )

    @application.post("/upload")
    async def upload(request: Request):
        return {"size": len(await request.body())}

    def chunks():
        yield b"123456"
        yield b"78901"

    with TestClient(application) as client:
        response = client.post(
            "/upload",
            content=chunks(),
            headers={"Transfer-Encoding": "chunked"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.json()["error"]["details"] == {"maximum_bytes": 10}
