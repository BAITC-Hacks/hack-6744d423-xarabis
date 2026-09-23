from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from city_simulator.core.config import get_settings
from city_simulator.domain.exceptions import ScenarioValidationError
from city_simulator.presentation.dependencies import get_repository
from city_simulator.presentation.routes import router


def create_app() -> FastAPI:
    settings = get_settings()
    # Fail fast if the bundled dataset is incomplete or internally inconsistent.
    get_repository().get_dataset()
    application = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="API симулятора управления районами Астаны.",
        debug=settings.debug,
    )

    @application.exception_handler(ScenarioValidationError)
    async def scenario_validation_handler(
        _request: Request,
        exc: ScenarioValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "scenario_validation_error", "details": exc.errors},
        )

    @application.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "docs": "/docs"}

    application.include_router(router, prefix=settings.api_v1_prefix)
    return application


app = create_app()
