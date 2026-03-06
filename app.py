"""FastAPI application factory -- EquityIQ entry point."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request

from config import get_settings, setup_logging
from config.logging import get_logger

logger = get_logger(__name__)

health_router = APIRouter()


@health_router.get("/health")
async def health(request: Request) -> dict:
    """Liveness / readiness probe."""
    settings = request.app.state.settings
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "version": request.app.version,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan: startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings)
    app.state.settings = settings
    logger.info("EquityIQ starting up (env=%s)", settings.ENVIRONMENT)
    yield
    logger.info("EquityIQ shutting down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(title="EquityIQ", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    return app


app = create_app()
