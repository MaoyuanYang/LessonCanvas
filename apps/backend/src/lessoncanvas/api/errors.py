from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    status_code = 500
    code = "UNEXPECTED"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthRequiredError(ApiError):
    status_code = 401
    code = "AUTH_REQUIRED"


class NotFoundError(ApiError):
    status_code = 404
    code = "NOT_FOUND"


class RequirementError(ApiError):
    status_code = 422
    code = "REQUIREMENT"


class QuotaExceededError(ApiError):
    status_code = 429
    code = "QUOTA_EXCEEDED"


class ProviderTransientError(ApiError):
    status_code = 503
    code = "PROVIDER_TRANSIENT"


def render_error(request: Request, error: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "correlation_id": getattr(request.state, "correlation_id", None),
                "details": error.details,
            }
        },
    )
