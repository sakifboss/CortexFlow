"""
Domain-driven exception hierarchy + FastAPI handlers.

All application errors derive from AppError and carry an HTTP status + stable
error code so the frontend can branch on `code` rather than parsing messages.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger


class AppError(Exception):
    """Base application error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str = "", *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message or self.__class__.__name__
        self.details = details or {}


# ── 4xx ──────────────────────────────────────────────────────
class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


# ── 5xx ──────────────────────────────────────────────────────
class InfrastructureError(AppError):
    status_code = 503
    code = "infrastructure_error"


# ── Handlers ─────────────────────────────────────────────────
def _error(code: str, message: str, status_code: int, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            }
        ),
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.exception("Unhandled app error: {}", exc.message)
    return _error(exc.code, exc.message, exc.status_code, exc.details)


async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _error("validation_error", "Request validation failed", 422, exc.errors())


async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return _error("internal_error", "Internal server error", 500)


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, unhandled_handler)
