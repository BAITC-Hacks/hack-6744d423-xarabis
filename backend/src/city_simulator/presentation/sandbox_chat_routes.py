"""Sandbox SSE enters through the same backend as scenario chat."""

import json
from typing import Any, Literal

import anyio
import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from city_simulator.core.config import get_settings

router = APIRouter(prefix="/sandbox", tags=["consultant"])


class ClosingStreamingResponse(StreamingResponse):
    def __init__(self, *args, close_upstream, **kwargs):
        super().__init__(*args, **kwargs)
        self.close_upstream = close_upstream

    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await self.body_iterator.aclose()
                finally:
                    await self.close_upstream()


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class SandboxChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=4000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)
    context: dict[str, Any]


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


async def relay(payload: SandboxChatRequest, path: str):
    settings = get_settings()
    client = httpx.AsyncClient(
        base_url=settings.ai_service_url,
        timeout=settings.ai_service_timeout_seconds,
        follow_redirects=False,
    )
    upstream = None

    async def close():
        # Browser disconnect cancellation must still release upstream resources.
        with anyio.CancelScope(shield=True):
            if upstream is not None:
                await upstream.aclose()
            await client.aclose()

    try:
        request = client.build_request(
            "POST", path, json=payload.model_dump(), headers={"Accept": "text/event-stream"}
        )
        upstream = await client.send(request, stream=True)
    except httpx.TimeoutException:
        await close()
        return error_response(504, "ai_timeout", "ИИ-сервис не ответил вовремя.")
    except httpx.HTTPError:
        await close()
        return error_response(503, "ai_unavailable", "ИИ-сервис временно недоступен.")
    except BaseException:
        await close()
        raise

    if upstream.status_code != 200:
        status = upstream.status_code if upstream.status_code in {422, 429, 504} else 503
        await close()
        return error_response(status, "ai_unavailable", "ИИ-сервис отклонил запрос.")
    if not upstream.headers.get("content-type", "").startswith("text/event-stream"):
        await close()
        return error_response(502, "invalid_ai_response", "ИИ-сервис вернул неверный формат.")

    async def events():
        deadline = anyio.current_time() + settings.ai_service_timeout_seconds
        chunks = upstream.aiter_bytes()
        try:
            while True:
                # Do not suspend at yield inside a cancel scope: disconnect cleanup
                # may close the iterator under a different enclosing scope.
                with anyio.fail_after(max(0, deadline - anyio.current_time())):
                    try:
                        chunk = await anext(chunks)
                    except StopAsyncIteration:
                        break
                yield chunk
        except (httpx.HTTPError, TimeoutError):
            data = json.dumps(
                {"error": {"code": "ai_stream_interrupted", "message": "Поток ответа ИИ прерван."}},
                ensure_ascii=False,
            )
            yield f"event: error\ndata: {data}\n\n".encode()
        finally:
            await close()

    return ClosingStreamingResponse(
        events(),
        close_upstream=close,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/stream")
async def sandbox_stream(payload: SandboxChatRequest):
    return await relay(payload, "/sandbox/chat/stream")


@router.post("/v2/chat/stream")
async def district_stream(payload: SandboxChatRequest):
    return await relay(payload, "/sandbox/v2/chat/stream")
