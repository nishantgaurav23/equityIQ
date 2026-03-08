# Spec S6.2 -- A2A Protocol Server Factory

## Overview

Reusable factory function that creates a FastAPI sub-application with A2A protocol endpoints for any EquityIQ agent. Each agent gets a `/.well-known/agent-card.json` discovery endpoint, a JSONRPC handler for `tasks/send` messages, and a health check -- all wired up from a `BaseAnalystAgent` instance.

## Location

`agents/a2a_server.py`

## Dependencies

| Spec | What it provides |
|------|-----------------|
| S6.1 | `agents/base_agent.py` -- BaseAnalystAgent class with analyze(), get_agent_card() |
| S1.4 | `app.py` -- FastAPI application factory (lifespan, health router) |

## Public API

### `create_agent_server(agent: BaseAnalystAgent) -> FastAPI`

Factory function that builds a FastAPI app with A2A protocol endpoints for the given agent.

```python
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
```

### Endpoints

#### `GET /.well-known/agent-card.json`

Returns the agent's A2A discovery card (from `agent.get_agent_card()`).

Response (200 OK):
```json
{
  "name": "valuation_scout",
  "description": "Senior equity research analyst specializing in fundamental stock valuation.",
  "url": "http://localhost:8001",
  "capabilities": ["get_fundamentals"],
  "output_schema": "ValuationReport"
}
```

#### `POST /a2a`

JSONRPC 2.0 handler for A2A protocol messages. Supports the `tasks/send` method.

Request body:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tasks/send",
  "params": {
    "id": "task-456",
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "AAPL"}]
    }
  }
}
```

Response (200 OK, success):
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "id": "task-456",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "parts": [{"type": "text", "text": "{...serialized report...}"}]
      }
    ]
  }
}
```

Response (200 OK, agent error -- graceful):
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "id": "task-456",
    "status": {
      "state": "completed"
    },
    "artifacts": [
      {
        "parts": [{"type": "text", "text": "{...fallback HOLD report...}"}]
      }
    ]
  }
}
```

Response (200 OK, protocol error):
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "error": {
    "code": -32601,
    "message": "Method not found: unknown/method"
  }
}
```

JSONRPC error codes:
- `-32600`: Invalid request (missing required fields)
- `-32601`: Method not found (unsupported method)
- `-32602`: Invalid params (missing ticker in message)

#### `GET /health`

Returns agent health status.

Response (200 OK):
```json
{
  "status": "ok",
  "agent": "valuation_scout"
}
```

## Implementation Details

### Pydantic Models (internal to module)

```python
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
```

### JSONRPC Handler Flow

1. Validate the JSONRPC request body via Pydantic
2. Check `method` is `"tasks/send"` -- return `-32601` error for unknown methods
3. Extract ticker from `params.message.parts[0].text`
4. If no text part found, return `-32602` error
5. Call `agent.analyze(ticker)` -- this never raises (BaseAnalystAgent guarantee)
6. Serialize the report to JSON via `report.model_dump_json()`
7. Return JSONRPC result with task status `completed` and report as artifact

### Error Handling

- Invalid JSONRPC body (validation error) -> return `-32600` error
- Unknown method -> return `-32601` error
- Missing ticker text -> return `-32602` error
- Agent analysis failure -> still returns `completed` status with fallback HOLD report (BaseAnalystAgent handles this internally)
- The `/a2a` endpoint never returns HTTP errors for protocol issues -- all errors are JSONRPC-level

### Integration with Main App

The server created by `create_agent_server()` can be:
1. Run standalone: `uvicorn agents.a2a_server:app --port 8001` (for development)
2. Mounted as sub-app on the main FastAPI app (for monolith deployment)

The factory returns a complete FastAPI app, not just a router, so it can function independently or be composed.

## Tangible Outcomes

1. `agents/a2a_server.py` exists with `create_agent_server()` factory function
2. All tests pass: `python -m pytest tests/test_a2a_server.py -v`
3. `ruff check agents/a2a_server.py` passes with no errors
4. `GET /.well-known/agent-card.json` returns valid agent card dict
5. `POST /a2a` with `tasks/send` method runs agent analysis and returns JSONRPC result
6. `POST /a2a` with unknown method returns JSONRPC `-32601` error
7. `POST /a2a` with missing params returns JSONRPC `-32600` error
8. `GET /health` returns `{"status": "ok", "agent": "<name>"}`
9. Server works with any `BaseAnalystAgent` instance (reusable)

## Test Plan

### Unit Tests (`tests/test_a2a_server.py`)

Use `httpx.AsyncClient` with `ASGITransport` (or `TestClient`) to test the FastAPI app directly. Mock `BaseAnalystAgent.analyze()` to avoid real LLM calls.

1. **test_agent_card_endpoint** -- GET `/.well-known/agent-card.json` returns 200 with agent card
2. **test_agent_card_has_required_fields** -- response contains name, description, url, capabilities, output_schema
3. **test_health_endpoint** -- GET `/health` returns 200 with `{"status": "ok", "agent": "<name>"}`
4. **test_a2a_tasks_send_success** -- POST `/a2a` with valid tasks/send, mock analyze() returns report, verify JSONRPC result
5. **test_a2a_tasks_send_result_structure** -- result has id, status.state="completed", artifacts with parts
6. **test_a2a_tasks_send_artifact_contains_report** -- artifact text is valid JSON matching report
7. **test_a2a_tasks_send_preserves_task_id** -- result.id matches params.id
8. **test_a2a_unknown_method** -- POST `/a2a` with `method: "unknown/foo"` returns JSONRPC error -32601
9. **test_a2a_invalid_request_body** -- POST `/a2a` with malformed JSON returns 422 or JSONRPC error -32600
10. **test_a2a_missing_params** -- POST `/a2a` with tasks/send but no params returns JSONRPC error -32600
11. **test_a2a_missing_text_in_parts** -- POST `/a2a` with empty parts list returns JSONRPC error -32602
12. **test_a2a_agent_fallback_still_completes** -- mock analyze() to return fallback (HOLD/0.0), verify task state is still "completed"
13. **test_create_agent_server_returns_fastapi** -- factory returns FastAPI instance
14. **test_server_reusable_with_different_agents** -- create servers for two different mock agents, both work independently

All tests mock `BaseAnalystAgent` -- no real ADK/LLM calls.
