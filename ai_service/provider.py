"""OpenAI adapter with explicit history, strict output and a total deadline."""
import asyncio
from json import JSONDecodeError

import anyio
import httpx2
from openai import APIError, APIResponseValidationError, APITimeoutError, AsyncOpenAI
from pydantic import ValidationError

from .config import Settings
from .errors import AIError
from .knowledge import build_input, load_instructions
from .schemas import ChatRequest, ChatResponse
from .streaming import AnswerPreview


def output_format() -> dict:
    # Length limits stay enforced locally. Omitting these optional JSON Schema
    # constraints on the wire also supports models with a narrower schema subset.
    def portable(value):
        if isinstance(value, dict):
            return {key: portable(item) for key, item in value.items()
                    if key not in {'minLength', 'maxLength', 'minItems', 'maxItems'}}
        if isinstance(value, list):
            return [portable(item) for item in value]
        return value
    return {'type': 'json_schema', 'name': 'city_consultant_report', 'strict': True,
            'schema': portable(ChatResponse.model_json_schema())}


def parse_report(response) -> ChatResponse:
    # SDK response objects can be constructed permissively even for malformed
    # HTTP 200 envelopes. Validate the pieces we consume before dereferencing.
    output = getattr(response, 'output', None)
    if getattr(response, 'status', None) != 'completed' or not isinstance(output, list):
        raise AIError('invalid_ai_response')
    texts = []
    for item in output:
        item_type = getattr(item, 'type', None)
        if not isinstance(item_type, str):
            raise AIError('invalid_ai_response')
        if item_type != 'message':
            continue
        contents = getattr(item, 'content', None)
        if not isinstance(contents, list):
            raise AIError('invalid_ai_response')
        for content in contents:
            content_type = getattr(content, 'type', None)
            if content_type == 'refusal':
                raise AIError('ai_refusal')
            text = getattr(content, 'text', None)
            if content_type != 'output_text' or not isinstance(text, str):
                raise AIError('invalid_ai_response')
            texts.append(text)
    return ChatResponse.model_validate_json(''.join(texts))


class OpenAIProvider:
    def __init__(self, settings: Settings, http_client: httpx2.AsyncClient | None = None):
        self.settings = settings
        self.client = None
        if settings.configured:
            self.client = AsyncOpenAI(
                api_key=settings.api_key.get_secret_value().strip(),
                base_url='https://api.openai.com/v1',
                max_retries=0,
                timeout=settings.timeout_seconds,
                http_client=http_client,
            )

    async def generate(self, request: ChatRequest) -> ChatResponse:
        if self.client is None:
            raise AIError('ai_not_configured')
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                response = await self.client.responses.create(
                    model=self.settings.model.strip(),
                    instructions=load_instructions(),
                    input=build_input(request),
                    text={'format': output_format()},
                    store=False,
                    max_output_tokens=self.settings.max_output_tokens,
                )
            return parse_report(response)
        except (APITimeoutError, TimeoutError) as exc:
            raise AIError('ai_timeout') from exc
        except (ValidationError, APIResponseValidationError, JSONDecodeError) as exc:
            raise AIError('invalid_ai_response') from exc
        except APIError as exc:
            raise AIError('ai_unavailable') from exc

    async def close(self):
        if self.client is not None:
            await self.client.close()

    async def stream(self, request: ChatRequest):
        if self.client is None:
            raise AIError('ai_not_configured')
        upstream = None
        preview = AnswerPreview()
        channel = None
        try:
            async with asyncio.timeout(self.settings.timeout_seconds):
                upstream = await self.client.responses.create(
                    model=self.settings.model.strip(),
                    instructions=load_instructions(), input=build_input(request),
                    text={'format': output_format()}, store=False, stream=True,
                    max_output_tokens=self.settings.max_output_tokens,
                )
                async for event in upstream:
                    kind = getattr(event, 'type', None)
                    if not isinstance(kind, str):
                        raise AIError('invalid_ai_response')
                    if kind == 'response.output_text.delta':
                        current = (getattr(event, 'item_id', None),
                                   getattr(event, 'output_index', None),
                                   getattr(event, 'content_index', None))
                        if channel is not None and current != channel:
                            raise AIError('invalid_ai_response')
                        channel = current
                        difference = preview.feed(getattr(event, 'delta', None))
                        if difference:
                            yield 'answer_delta', {'delta': difference}
                    elif kind in ('response.refusal.delta', 'response.refusal.done'):
                        raise AIError('ai_refusal')
                    elif kind in ('response.failed', 'error'):
                        raise AIError('ai_unavailable')
                    elif kind == 'response.incomplete':
                        raise AIError('invalid_ai_response')
                    elif kind == 'response.completed':
                        report = parse_report(getattr(event, 'response', None))
                        if preview.raw and ChatResponse.model_validate_json(preview.raw) != report:
                            raise AIError('invalid_ai_response')
                        if not report.answer.startswith(preview.text.rstrip()):
                            raise AIError('invalid_ai_response')
                        if len(report.answer) > len(preview.text):
                            yield 'answer_delta', {'delta': report.answer[len(preview.text):]}
                        yield 'complete', report.model_dump(mode='json')
                        return
                raise AIError('invalid_ai_response')
        except (APITimeoutError, TimeoutError) as exc:
            raise AIError('ai_timeout') from exc
        except (ValidationError, APIResponseValidationError, JSONDecodeError, UnicodeError) as exc:
            raise AIError('invalid_ai_response') from exc
        except APIError as exc:
            raise AIError('ai_unavailable') from exc
        finally:
            if upstream is not None:
                with anyio.CancelScope(shield=True):
                    await upstream.close()
