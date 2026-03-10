"""FastAPI exception handlers for structured error responses."""

import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from api.exceptions import (
    AnalysisTimeoutError,
    EquityIQError,
    InsufficientDataError,
    InvalidTickerError,
    TickerNotFoundError,
    VerdictNotFoundError,
)

logger = logging.getLogger(__name__)

# Map exception types to HTTP status codes
_STATUS_MAP: dict[type[EquityIQError], int] = {
    InvalidTickerError: 400,
    TickerNotFoundError: 404,
    VerdictNotFoundError: 404,
    InsufficientDataError: 422,
    AnalysisTimeoutError: 504,
}


def _error_response(status_code: int, code: str, message: str, details: dict | None = None):
    """Build a structured error JSONResponse."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(EquityIQError)
    async def handle_equityiq_error(request: Request, exc: EquityIQError):
        status_code = _STATUS_MAP.get(type(exc), 500)
        level = logging.WARNING if status_code < 500 else logging.ERROR
        logger.log(level, "%s: %s", exc.error_code, exc.message)
        return _error_response(status_code, exc.error_code, exc.message, exc.details)

    @app.exception_handler(asyncio.TimeoutError)
    async def handle_timeout_error(request: Request, exc: asyncio.TimeoutError):
        logger.error("Analysis timed out: %s", exc)
        return _error_response(504, "ANALYSIS_TIMEOUT", "Analysis timed out")

    @app.exception_handler(Exception)
    async def handle_unhandled_error(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
