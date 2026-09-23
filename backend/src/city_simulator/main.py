from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from city_simulator.core.config import get_settings
from city_simulator.core.logging import configure_logging
from city_simulator.domain.exceptions import (
    ConsultantServiceError,
    ScenarioNotFoundError,
    ScenarioValidationError,
    ScenarioVersionConflictError,
    SimulationResultNotFoundError,
)
from city_simulator.infrastructure.database import dispose_engine
from city_simulator.presentation.chat_routes import router as chat_router
from city_simulator.presentation.dependencies import close_consultant_gateway, get_repository
from city_simulator.presentation.middleware import (
    REQUEST_ID_HEADER,
    ChatRateLimitMiddleware,
    RequestContextMiddleware,
)
from city_simulator.presentation.routes import router
from city_simulator.presentation.scenario_routes import router as scenario_router


@asynccontextmanager
async def lifespan(_application: FastAPI):
    try:
        yield
    finally:
        await close_consultant_gateway()
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    # Fail fast if the bundled dataset is incomplete or internally inconsistent.
    get_repository().get_dataset()
    application = FastAPI(
        title=settings.app_name,
        version="0.6.0",
        description="API симулятора управления районами Астаны.",
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    # Starlette executes the last registered middleware first. Keep CORS outermost
    # so browser clients can inspect errors produced by the request guards too.
    application.add_middleware(
        ChatRateLimitMiddleware,
        requests_per_minute=settings.ai_chat_requests_per_minute,
    )
    application.add_middleware(
        RequestContextMiddleware,
        max_request_body_bytes=settings.max_request_body_bytes,
        debug=settings.app_debug,
    )
    if settings.allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins,
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER, "Retry-After"],
        )

    @application.exception_handler(ScenarioValidationError)
    async def scenario_validation_handler(
        _request: Request,
        exc: ScenarioValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "scenario_validation_error",
                    "message": "Сценарий нарушает игровые правила",
                    "details": [
                        {
                            "code": issue.code,
                            "message": issue.message,
                            "context": issue.context,
                        }
                        for issue in exc.issues
                    ],
                }
            },
        )

    @application.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Запрос не соответствует контракту API",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )

    @application.exception_handler(ScenarioNotFoundError)
    async def scenario_not_found_handler(
        _request: Request,
        exc: ScenarioNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "scenario_not_found",
                    "message": str(exc),
                    "details": {"scenario_id": str(exc.scenario_id)},
                }
            },
        )

    @application.exception_handler(SimulationResultNotFoundError)
    async def result_not_found_handler(
        _request: Request,
        exc: SimulationResultNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "result_not_found",
                    "message": str(exc),
                    "details": {"scenario_id": str(exc.scenario_id)},
                }
            },
        )

    @application.exception_handler(ScenarioVersionConflictError)
    async def scenario_conflict_handler(
        _request: Request,
        exc: ScenarioVersionConflictError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "scenario_version_conflict",
                    "message": str(exc),
                    "details": {
                        "scenario_id": str(exc.scenario_id),
                        "expected_version": exc.expected_version,
                        "current_version": exc.current_version,
                    },
                }
            },
        )

    @application.exception_handler(ConsultantServiceError)
    async def consultant_error_handler(
        _request: Request,
        exc: ConsultantServiceError,
    ) -> JSONResponse:
        errors = {
            "ai_not_configured": (503, "AI-консультант не настроен"),
            "ai_unavailable": (503, "AI-консультант временно недоступен"),
            "ai_timeout": (504, "Превышено время ожидания ответа AI-консультанта"),
            "invalid_ai_response": (502, "AI-консультант вернул некорректный ответ"),
            "ai_refusal": (502, "AI-консультант отказался формировать ответ"),
            "ai_contract_mismatch": (502, "Нарушен контракт с AI-сервисом"),
        }
        status_code, message = errors.get(
            exc.code,
            (503, "AI-консультант временно недоступен"),
        )
        return JSONResponse(
            status_code=status_code,
            content={"error": {"code": exc.code, "message": message}},
        )

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    application.include_router(router, prefix=settings.api_v1_prefix)
    application.include_router(scenario_router, prefix=settings.api_v1_prefix)
    application.include_router(chat_router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
