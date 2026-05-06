"""problem+JSON error envelope per contracts/http-api.md.

Backend never returns rendered English copy (R6); it returns a stable error
code plus a `message_key` the frontend resolves through `strings.ts`.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vayobd.logging import get_logger
from vayobd.models import ProblemDetail

log = get_logger(__name__)


class ApiError(Exception):
    """Raise to return a problem+JSON body with a chosen status code."""

    def __init__(
        self,
        *,
        status_code: int,
        error: str,
        message_key: str,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.message_key = message_key
        super().__init__(f"{error}: {message_key}")


def _problem_response(
    *,
    status_code: int,
    error: str,
    message_key: str,
) -> JSONResponse:
    body = ProblemDetail(error=error, message_key=message_key)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        media_type="application/problem+json",
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        log.warning("api_error", error=exc.error, message_key=exc.message_key)
        return _problem_response(
            status_code=exc.status_code,
            error=exc.error,
            message_key=exc.message_key,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        log.info("request_validation_error", errors=exc.errors())
        return _problem_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="invalid_request",
            message_key="errors.invalid_request",
        )

    @app.exception_handler(Exception)
    async def _handle_uncaught(_: Request, exc: Exception) -> JSONResponse:
        log.error("uncaught_exception", error=type(exc).__name__, message=str(exc))
        return _problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="internal_error",
            message_key="errors.generic",
        )
