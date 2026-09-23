"""Incremental answer preview and SSE framing; final reports are validated separately."""
import json

import anyio
import jiter
from starlette.responses import StreamingResponse

from .errors import AIError


class AnswerPreview:
    def __init__(self):
        self.raw = ''
        self.text = ''

    def feed(self, delta: str) -> str:
        if not isinstance(delta, str):
            raise AIError('invalid_ai_response')
        self.raw += delta
        if len(self.raw) > 200_000:
            raise AIError('invalid_ai_response')
        try:
            parsed = jiter.from_json(self.raw.encode('utf-8'), partial_mode='trailing-strings',
                                     catch_duplicate_keys=True, allow_inf_nan=False)
        except (ValueError, UnicodeEncodeError):
            # A chunk may end inside a key, escape or UTF-16 surrogate pair.
            # No report is accepted until the complete JSON passes validation.
            return ''
        if not isinstance(parsed, dict):
            raise AIError('invalid_ai_response')
        candidate = parsed.get('answer', '')
        if not isinstance(candidate, str):
            raise AIError('invalid_ai_response')
        candidate = candidate.lstrip()
        if len(candidate) > 6000 or not candidate.startswith(self.text):
            raise AIError('invalid_ai_response')
        difference = candidate[len(self.text):]
        self.text = candidate
        return difference


def encode_event(name: str, data: dict) -> str:
    return f'event: {name}\ndata: {json.dumps(data, ensure_ascii=False, allow_nan=False)}\n\n'


class ClosingStreamingResponse(StreamingResponse):
    async def stream_response(self, send):
        try:
            await super().stream_response(send)
        finally:
            # A disconnect can interrupt send while the iterator is suspended at yield.
            # Close it explicitly, including under Starlette's cancellation scope.
            with anyio.CancelScope(shield=True):
                await self.body_iterator.aclose()
