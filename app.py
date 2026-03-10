"""FastAPI application factory -- EquityIQ entry point."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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
    import os

    settings = get_settings()
    setup_logging(settings)

    # Local dev: export API keys to OS environment so Google ADK and other SDKs
    # can find them. On GCP, Secret Manager injects these directly — this is a
    # no-op when the env var is already set.
    for key in ("GOOGLE_API_KEY", "POLYGON_API_KEY", "FRED_API_KEY", "NEWS_API_KEY"):
        val = getattr(settings, key, None)
        if val and not os.environ.get(key):
            os.environ[key] = val
    app.state.settings = settings

    # Initialize memory layer
    from memory.history_retriever import HistoryRetriever
    from memory.insight_vault import InsightVault

    vault = InsightVault()
    await vault.initialize()
    app.state.vault = vault

    # Initialize history retriever
    app.state.history_retriever = HistoryRetriever(vault)

    # Initialize orchestrator
    from agents.market_conductor import MarketConductor

    app.state.conductor = MarketConductor(vault=vault)

    # Initialize Vertex Memory Bank for chat
    from memory.vertex_memory import VertexMemoryBank

    vertex_memory = VertexMemoryBank()
    try:
        await vertex_memory.initialize()
    except Exception:
        logger.warning("VertexMemoryBank init failed; chat will run without persistence")
        vertex_memory = None
    app.state.vertex_memory = vertex_memory

    # Initialize Chat Engine
    from api.chat import ChatEngine

    app.state.chat_engine = ChatEngine(
        conductor=app.state.conductor,
        memory=vertex_memory,
        vault=vault,
    )

    logger.info("EquityIQ starting up (env=%s)", settings.ENVIRONMENT)
    yield

    # Cleanup
    if vertex_memory:
        await vertex_memory.close()
    await vault.close()
    logger.info("EquityIQ shutting down")


def create_app() -> FastAPI:
    """Build and return the FastAPI application."""
    app = FastAPI(
        title="EquityIQ",
        version="0.1.0",
        description="Multi-agent stock intelligence system",
        lifespan=lifespan,
    )

    # CORS -- allow local frontend and Swagger UI
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    from api.error_handlers import register_error_handlers

    register_error_handlers(app)

    # Health endpoint
    app.include_router(health_router)

    # API routes
    from api.routes import router as api_router

    app.include_router(api_router)

    # Chat routes
    from api.chat import chat_router

    app.include_router(chat_router)

    return app


app = create_app()
