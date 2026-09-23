import json

import httpx
import pytest
from fastapi.testclient import TestClient

from city_simulator.main import create_app


@pytest.fixture
def gateway(monkeypatch):
    seen = []
    clients = []
    result = {
        "status": 200,
        "type": "text/event-stream",
        "body": 'event: answer_delta\ndata: {"delta":"Привет"}\n\n'
        'event: complete\ndata: {"answer":"Привет"}\n\n',
    }

    def respond(request):
        seen.append(request)
        if result.get("timeout"):
            raise httpx.ReadTimeout("private upstream information")
        return httpx.Response(
            result["status"],
            headers={"Content-Type": result["type"]},
            content=result["body"].encode(),
        )

    original = httpx.AsyncClient

    def make_client(**kwargs):
        client = original(**kwargs, transport=httpx.MockTransport(respond))
        clients.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return seen, clients, result


@pytest.mark.parametrize("version", ["", "v2/"])
def test_backend_relays_sandbox_stream_to_fixed_ai_path(gateway, version):
    seen, clients, result = gateway
    payload = {"message": "Совет", "history": [], "context": {"quarter": 1}}
    response = TestClient(create_app()).post(f"/api/v1/sandbox/{version}chat/stream", json=payload)
    assert response.status_code == 200
    assert response.text == result["body"]
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["x-accel-buffering"] == "no"
    assert seen[0].url.path == f"/sandbox/{version}chat/stream"
    assert json.loads(seen[0].content) == payload
    assert all(client.is_closed for client in clients)


@pytest.mark.parametrize("status,expected", [(422, 422), (500, 503), (401, 503)])
def test_upstream_errors_are_sanitized_and_connections_closed(gateway, status, expected):
    _, clients, result = gateway
    result.update(status=status, body="private upstream information", type="text/plain")
    response = TestClient(create_app()).post(
        "/api/v1/sandbox/v2/chat/stream", json={"message": "Hi", "context": {}}
    )
    assert response.status_code == expected
    assert "private upstream" not in response.text
    assert all(client.is_closed for client in clients)


def test_timeout_does_not_leak_upstream_details(gateway):
    _, clients, result = gateway
    result["timeout"] = True
    response = TestClient(create_app()).post(
        "/api/v1/sandbox/v2/chat/stream", json={"message": "Hi", "context": {}}
    )
    assert response.status_code == 504
    assert "private upstream" not in response.text
    assert all(client.is_closed for client in clients)


def test_invalid_message_never_calls_ai(gateway):
    seen, _, _ = gateway
    response = TestClient(create_app()).post(
        "/api/v1/sandbox/v2/chat/stream", json={"message": "", "context": {}}
    )
    assert response.status_code == 422
    assert not seen


@pytest.mark.asyncio
@pytest.mark.parametrize("disconnect_at", ["headers", "body"])
async def test_early_delivery_and_disconnect_close_upstream(monkeypatch, disconnect_at):
    from city_simulator.presentation.sandbox_chat_routes import SandboxChatRequest, relay

    class Source(httpx.AsyncByteStream):
        closed = False
        advanced = False

        async def __aiter__(self):
            yield b'event: answer_delta\ndata: {"delta":"Hi"}\n\n'
            self.advanced = True
            raise AssertionError("must deliver first frame before requesting more")

        async def aclose(self):
            self.closed = True

    source = Source()
    client = httpx.AsyncClient(
        base_url="http://ai.test",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=source
            )
        ),
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    response = await relay(SandboxChatRequest(message="Hi", context={}), "/sandbox/v2/chat/stream")

    async def send(message):
        if disconnect_at == "headers" or message["type"] == "http.response.body":
            if disconnect_at == "body":
                assert b"answer_delta" in message["body"]
                assert not source.advanced
            raise OSError("browser disconnected")

    with pytest.raises(OSError):
        await response.stream_response(send)
    assert source.closed
    assert client.is_closed


def test_sandbox_versions_share_backend_rate_limit(gateway, monkeypatch):
    from city_simulator.core.config import get_settings

    monkeypatch.setattr(get_settings(), "ai_chat_requests_per_minute", 1)
    client = TestClient(create_app())
    payload = {"message": "Hi", "context": {}}
    assert client.post("/api/v1/sandbox/chat/stream", json=payload).status_code == 200
    assert client.post("/api/v1/sandbox/v2/chat/stream", json=payload).status_code == 429
    assert len(gateway[0]) == 1
