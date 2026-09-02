import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lessoncanvas.api.account import router as account_router
from lessoncanvas.api.alignment import router as alignment_router
from lessoncanvas.api.auth import router as auth_router
from lessoncanvas.api.blueprint import router as blueprint_router
from lessoncanvas.api.brief import router as brief_router
from lessoncanvas.api.decks import deck_router as decks_artifact_router
from lessoncanvas.api.decks import router as decks_router
from lessoncanvas.api.delivery import router as delivery_router
from lessoncanvas.api.deps import require_general_rate
from lessoncanvas.api.discovery import router as discovery_router
from lessoncanvas.api.errors import ApiError, render_error
from lessoncanvas.api.evidence import router as evidence_router
from lessoncanvas.api.exercises import exercise_router as exercises_artifact_router
from lessoncanvas.api.exercises import router as exercises_router
from lessoncanvas.api.generation import lesson_router as generation_lesson_router
from lessoncanvas.api.generation import router as generation_router
from lessoncanvas.api.memory import project_router as memory_project_router
from lessoncanvas.api.memory import router as memory_router
from lessoncanvas.api.planning import router as planning_router
from lessoncanvas.api.product_validation import router as product_validation_router
from lessoncanvas.api.projects import router as projects_router
from lessoncanvas.api.sample import router as sample_router
from lessoncanvas.api.sources import router as sources_router
from lessoncanvas.api.technical_evaluation import router as technical_evaluation_router
from lessoncanvas.api.versions import router as versions_router
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

    # F011 D1/D2: the general request-rate guard covers every authenticated
    # route uniformly; expensive-write endpoints add their own stricter class
    # at the route level. /health stays unguarded (unauthenticated probe).
    all_routers = (
        projects_router,
        sources_router,
        discovery_router,
        brief_router,
        planning_router,
        blueprint_router,
        generation_router,
        generation_lesson_router,
        decks_router,
        decks_artifact_router,
        exercises_router,
        exercises_artifact_router,
        account_router,
        evidence_router,
        versions_router,
        alignment_router,
        delivery_router,
        technical_evaluation_router,
        product_validation_router,
        sample_router,
        memory_router,
        memory_project_router,
    )
    for router in all_routers:
        app.include_router(router, dependencies=[Depends(require_general_rate)])

    # ADR-0006 D11: token issuance precedes workspace existence, so it stays
    # outside the workspace-scoped general-rate guard. It is unauthenticated
    # by design and discloses nothing.
    app.include_router(auth_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "database": check_database()}

    return app


app = create_app()
