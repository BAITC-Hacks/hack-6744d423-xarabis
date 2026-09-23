import logging
import re
from asyncio import Lock
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from math import ceil
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
logger = logging.getLogger("city_simulator.http")


class _RequestTooLargeError(Exception):
    pass


def get_request_id() -> str | None:
    return _request_id.get()


class ChatRateLimitMiddleware(BaseHTTPMiddleware):
    _chat_path = re.compile(r"/scenarios/([^/]+)/chat/messages$")
    _sandbox_path = re.compile(r"/sandbox/(?:v2/)?chat/stream$")

    def __init__(self, app, *, requests_per_minute: int) -> None:
        super().__init__(app)
        self._limit = requests_per_minute
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        match = self._chat_path.search(request.url.path)
        sandbox = self._sandbox_path.search(request.url.path)
        if request.method != "POST" or (match is None and sandbox is None):
            return await call_next(request)

        now = perf_counter()
        scenario_id = (
            match.group(1)
            if match
            else f"sandbox:{request.client.host if request.client else 'unknown'}"
        )
        async with self._lock:
            entries = self._requests[scenario_id]
            while entries and entries[0] <= now - 60:
                entries.popleft()
            if len(entries) >= self._limit:
                retry_after = max(1, ceil(60 - (now - entries[0])))
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "error": {
                            "code": "chat_rate_limit_exceeded",
                            "message": "Слишком много запросов к AI-консультанту",
                            "details": {"retry_after_seconds": retry_after},
                            "request_id": get_request_id(),
                        }
                    },
                )
            entries.append(now)
            if len(self._requests) > 1024:
                self._remove_expired_keys(now)
        return await call_next(request)

    def _remove_expired_keys(self, now: float) -> None:
        expired = [
            key for key, entries in self._requests.items() if not entries or entries[-1] <= now - 60
        ]
        for key in expired:
            self._requests.pop(key, None)


class RequestContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_body_bytes: int,
        debug: bool,
    ) -> None:
        self._app = app
        self._max_request_body_bytes = max_request_body_bytes
        self._debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid4())
        token = _request_id.set(request_id)
        started = perf_counter()
        status_code = 500
        response_started = False
        received_bytes = 0

        async def receive_with_limit() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self._max_request_body_bytes:
                    raise _RequestTooLargeError
            return message

        async def send_with_headers(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
                response_headers["X-Content-Type-Options"] = "nosniff"
                response_headers["X-Frame-Options"] = "DENY"
                response_headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        try:
            content_length = self._content_length(headers)
            if content_length is not None and content_length > self._max_request_body_bytes:
                response = JSONResponse(
                    status_code=413,
                    content=self._too_large_payload(request_id),
                )
                await response(scope, receive, send_with_headers)
            else:
                await self._app(scope, receive_with_limit, send_with_headers)
        except _RequestTooLargeError:
            if response_started:
                raise
            response = JSONResponse(
                status_code=413,
                content=self._too_large_payload(request_id),
            )
            await response(scope, receive, send_with_headers)
        except Exception:
            logger.exception(
                "unhandled_request_error",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                },
            )
            if self._debug or response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_error",
                        "message": "Внутренняя ошибка сервера",
                        "request_id": request_id,
                    }
                },
            )
            await response(scope, receive, send_with_headers)
        finally:
            duration_ms = round((perf_counter() - started) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            _request_id.reset(token)

    def _too_large_payload(self, request_id: str) -> dict[str, Any]:
        return {
            "error": {
                "code": "request_too_large",
                "message": "Размер запроса превышает допустимый лимит",
                "details": {"maximum_bytes": self._max_request_body_bytes},
                "request_id": request_id,
            }
        }

    @staticmethod
    def _content_length(headers: Headers) -> int | None:
        raw = headers.get("content-length")
        if raw is None:
            return None
        try:
            return max(0, int(raw))
        except ValueError:
            return None
