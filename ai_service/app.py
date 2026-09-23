"""HTTP boundary; the external backend owns sessions and simulation results."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import Settings
from .errors import AIError
from .provider import OpenAIProvider
from .schemas import ChatRequest, ChatResponse, ErrorResponse


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

    return application


app = create_app()
