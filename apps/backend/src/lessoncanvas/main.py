import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lessoncanvas.api.account import router as account_router
from lessoncanvas.api.blueprint import router as blueprint_router
from lessoncanvas.api.brief import router as brief_router
from lessoncanvas.api.discovery import router as discovery_router
from lessoncanvas.api.errors import ApiError, render_error
from lessoncanvas.api.planning import router as planning_router
from lessoncanvas.api.projects import router as projects_router
from lessoncanvas.api.sources import router as sources_router
from lessoncanvas.api.trace import router as trace_router
from lessoncanvas.db import check_database
from lessoncanvas.settings import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="LessonCanvas API", version="0.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["authorization", "content-type", "x-correlation-id"],
        expose_headers=["x-correlation-id"],
    )

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        request.state.correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["x-correlation-id"] = request.state.correlation_id
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return render_error(request, error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        fields = {str(e.get("loc", "")): e.get("msg", "") for e in error.errors()}
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "REQUIREMENT",
                    "message": "validation failed",
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "details": {"fields": fields},
                }
            },
        )

    app.include_router(projects_router)
    app.include_router(sources_router)
    app.include_router(discovery_router)
    app.include_router(brief_router)
    app.include_router(planning_router)
    app.include_router(blueprint_router)
    app.include_router(account_router)
    app.include_router(trace_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": check_database()}

    return app


app = create_app()
