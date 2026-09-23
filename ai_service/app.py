"""HTTP boundary; the external backend owns sessions and simulation results."""
from contextlib import aclosing, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .district_schemas import SandboxV2ChatRequest
from .errors import AIError
from .provider import OpenAIProvider
from .schemas import ChatRequest, ChatResponse, ErrorResponse, SandboxChatRequest
from .streaming import ClosingStreamingResponse, encode_event


def create_app(settings: Settings | None = None, provider: OpenAIProvider | None = None) -> FastAPI:
    configured_provider = provider if provider is not None else OpenAIProvider(settings if settings is not None else Settings.from_env())

    @asynccontextmanager
    async def lifespan(application):
        try:
            yield
        finally:
            await configured_provider.close()

    application = FastAPI(
        title='Аким — ИИ-консультант', version='0.1.0', lifespan=lifespan,
        description='Backend передаёт историю и актуальный расчёт; консультант возвращает блоки ответа. История не хранится.',
    )

    @application.exception_handler(AIError)
    async def ai_error_handler(request: Request, error: AIError):
        return JSONResponse(status_code=error.status_code, content=error.payload())

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, error: RequestValidationError):
        # Do not reflect potentially private messages, raw values or provider details.
        public_error = AIError('invalid_request')
        return JSONResponse(status_code=422, content=public_error.payload())

    @application.get('/health', summary='Проверка процесса без вызова модели')
    async def health():
        return {'status': 'ok'}

    @application.post('/chat', response_model=ChatResponse,
                      responses={code: {'model': ErrorResponse} for code in (422, 502, 503, 504)},
                      summary='Ответ консультанта по текущему сценарию')
    async def chat(payload: ChatRequest):
        return await configured_provider.generate(payload)

    @application.post('/sandbox/chat', response_model=ChatResponse,
                      responses={code: {'model': ErrorResponse} for code in (422, 502, 503, 504)},
                      summary='Консультант вымышленного города Новый Берег')
    async def sandbox_chat(payload: SandboxChatRequest):
        return await configured_provider.generate(payload)

    @application.post('/sandbox/v2/chat', response_model=ChatResponse,
                      responses={code: {'model': ErrorResponse} for code in (422, 502, 503, 504)},
                      summary='Консультант пяти районов вымышленного Нового Берега')
    async def sandbox_v2_chat(payload: SandboxV2ChatRequest):
        return await configured_provider.generate(payload)

    @application.post('/chat/stream', response_class=ClosingStreamingResponse,
                      responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}},
                                       'description': 'answer_delta, then complete or error; see README'},
                                 422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}},
                      summary='Поток текста ответа и проверенный итоговый отчёт')
    async def chat_stream(payload: ChatRequest):
        return streaming_response(payload)

    @application.post('/sandbox/chat/stream', response_class=ClosingStreamingResponse,
                      responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}},
                                       'description': 'answer_delta, then complete or error; see README'},
                                 422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}},
                      summary='Поток ответа консультанта вымышленного города')
    async def sandbox_chat_stream(payload: SandboxChatRequest):
        return streaming_response(payload)

    @application.post('/sandbox/v2/chat/stream', response_class=ClosingStreamingResponse,
                      responses={200: {'content': {'text/event-stream': {'schema': {'type': 'string'}}},
                                       'description': 'answer_delta, then complete or error; see README'},
                                 422: {'model': ErrorResponse}, 503: {'model': ErrorResponse}},
                      summary='Поток ответа консультанта пяти вымышленных районов')
    async def sandbox_v2_chat_stream(payload: SandboxV2ChatRequest):
        return streaming_response(payload)

    def streaming_response(payload: ChatRequest | SandboxChatRequest | SandboxV2ChatRequest):
        if not configured_provider.settings.configured:
            raise AIError('ai_not_configured')

        async def events():
            yield ': connected\n\n'
            try:
                async with aclosing(configured_provider.stream(payload)) as stream:
                    async for name, data in stream:
                        yield encode_event(name, data)
            except AIError as error:
                yield encode_event('error', error.payload())

        return ClosingStreamingResponse(events(), media_type='text/event-stream',
                                        headers={'Cache-Control': 'no-cache, no-transform',
                                                 'X-Accel-Buffering': 'no'})

    return application


app = create_app()
