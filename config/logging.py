"""Structured logging setup -- colorlog for local, JSON for production."""

import contextvars
import json
import logging
from datetime import datetime, timezone

import colorlog

from config.settings import Settings, get_settings

# Context variable for request tracing
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="no-request-id"
)


def get_request_id() -> str:
    """Return the current request ID from context."""
    return request_id_var.get()


def set_request_id(rid: str) -> None:
    """Set the request ID in the current context."""
    request_id_var.set(rid)


class JsonFormatter(logging.Formatter):
    """Structured JSON formatter for production (GCP Cloud Logging compatible)."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        return json.dumps(log_entry)


def setup_logging(settings: Settings | None = None) -> None:
    """Configure the root logger based on environment settings."""
    if settings is None:
        settings = get_settings()

    root = logging.getLogger()

    # Clear existing handlers to avoid duplicates
    root.handlers.clear()

    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    handler = logging.StreamHandler()

    if settings.is_production:
        handler.setFormatter(JsonFormatter())
    else:
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(name)s%(reset)s | %(message)s",
            log_colors={
                "DEBUG": "white",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        )
        handler.setFormatter(formatter)

    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)
