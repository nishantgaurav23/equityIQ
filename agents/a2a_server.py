"""A2A protocol server factory for EquityIQ agents."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from agents.base_agent import BaseAnalystAgent

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# A2A protocol models (JSONRPC 2.0)
# ---------------------------------------------------------------------------


class A2ATextPart(BaseModel):
    """A text part in an A2A message."""

    type: str = "text"
    text: str


class A2AMessage(BaseModel):
    """A2A protocol message."""

    role: str
    parts: list[A2ATextPart]


class A2ATaskParams(BaseModel):
    """Parameters for tasks/send."""

    id: str
    message: A2AMessage


class A2ARequest(BaseModel):
    """JSONRPC 2.0 request for A2A protocol."""

    jsonrpc: str = "2.0"
    id: str | int
    method: str
    params: A2ATaskParams | None = None


# ---------------------------------------------------------------------------
# JSONRPC helpers
# ---------------------------------------------------------------------------


def _jsonrpc_error(req_id: str | int | None, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }


def _jsonrpc_result(req_id: str | int, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_agent_server(agent: BaseAnalystAgent) -> FastAPI:
    """Create a FastAPI app with A2A protocol endpoints for an agent.

    Endpoints:
    - GET  /.well-known/agent-card.json  -> agent card for discovery
    - POST /a2a                          -> JSONRPC handler (tasks/send)
    - GET  /health                       -> health check

    Args:
        agent: A configured BaseAnalystAgent instance.

    Returns:
        FastAPI app ready to be mounted or run with uvicorn.
    """
    app = FastAPI(title=f"EquityIQ -- {agent.name}")

    @app.get("/.well-known/agent-card.json")
    async def agent_card() -> dict:
        return agent.get_agent_card()

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "agent": agent.name}

    @app.post("/a2a")
    async def a2a_handler(request: Request) -> JSONResponse:
        body = await request.json()

        # Parse and validate the JSONRPC request.
        try:
            req = A2ARequest.model_validate(body)
        except ValidationError:
            return JSONResponse(
                _jsonrpc_error(body.get("id"), -32600, "Invalid request"),
            )

        # Require params for tasks/send.
        if req.params is None:
            return JSONResponse(
                _jsonrpc_error(req.id, -32600, "Invalid request: missing params"),
            )

        # Only tasks/send is supported.
        if req.method != "tasks/send":
            return JSONResponse(
                _jsonrpc_error(req.id, -32601, f"Method not found: {req.method}"),
            )

        # Extract ticker from message parts.
        ticker: str | None = None
        for part in req.params.message.parts:
            if part.text:
                ticker = part.text.strip()
                break

        if not ticker:
            return JSONResponse(
                _jsonrpc_error(req.id, -32602, "Invalid params: no ticker in message"),
            )

        # Run analysis (never raises -- BaseAnalystAgent guarantee).
        report = await agent.analyze(ticker)

        return JSONResponse(
            _jsonrpc_result(
                req.id,
                {
                    "id": req.params.id,
                    "status": {"state": "completed"},
                    "artifacts": [
                        {
                            "parts": [
                                {"type": "text", "text": report.model_dump_json()},
                            ],
                        },
                    ],
                },
            ),
        )

    return app
