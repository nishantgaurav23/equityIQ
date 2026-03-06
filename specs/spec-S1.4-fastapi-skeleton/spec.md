# S1.4 -- FastAPI App Skeleton

## Meta
| Field | Value |
|-------|-------|
| Spec ID | S1.4 |
| Phase | 1 -- Project Foundation |
| Depends On | S1.3 (pydantic-settings) |
| Location | `app.py` |
| Status | spec-written |

## Overview
Create the FastAPI application factory with async lifespan management, a `/health` endpoint, and router inclusion pattern. This is the entry point for the entire backend.

## Functional Requirements

### FR-1: App Factory Function
- `create_app() -> FastAPI` function in `app.py`
- Returns a configured FastAPI instance
- Sets `title="EquityIQ"`, `version="0.1.0"`
- Attaches lifespan context manager

### FR-2: Async Lifespan
- Use FastAPI's `@asynccontextmanager` lifespan pattern
- **Startup**: Log "EquityIQ starting up", store settings in `app.state.settings`
- **Shutdown**: Log "EquityIQ shutting down"
- DB connection setup/teardown will be added in Phase 5 (S5.1)

### FR-3: Health Endpoint
- `GET /health` returns JSON: `{"status": "ok", "environment": "<env>", "version": "0.1.0"}`
- HTTP 200 on success
- Reads environment from `app.state.settings.ENVIRONMENT`

### FR-4: Router Inclusion Pattern
- Include a health router via `app.include_router()`
- Health endpoint lives in a router (not directly on app) for consistency with future API routers (S9.x)
- Router prefix: none (health at root `/health`)

### FR-5: Module-level App Instance
- `app = create_app()` at module level so uvicorn can find it via `app:app`
- This is what `make local-dev` will point to

## Non-Functional Requirements
- All async (lifespan is async context manager)
- No external API calls in this spec
- Settings loaded via `config.get_settings()`
- Import order: stdlib -> third-party -> local

## Test Plan
File: `tests/test_app.py`

| Test | Validates |
|------|-----------|
| `test_create_app_returns_fastapi` | FR-1: create_app() returns FastAPI instance |
| `test_app_title_and_version` | FR-1: title="EquityIQ", version="0.1.0" |
| `test_health_endpoint_returns_ok` | FR-3: GET /health -> 200, status=ok |
| `test_health_endpoint_has_environment` | FR-3: response includes environment field |
| `test_health_endpoint_has_version` | FR-3: response includes version field |
| `test_app_has_lifespan` | FR-2: app has lifespan configured |
| `test_module_level_app_exists` | FR-5: `app` variable exists at module level |

## Acceptance Criteria
1. `create_app()` returns a working FastAPI app
2. `GET /health` returns 200 with correct JSON shape
3. Lifespan logs startup/shutdown (verified by lifespan presence)
4. `uvicorn app:app --reload` starts without errors
5. All tests pass: `python -m pytest tests/test_app.py -v`
6. Ruff clean: `ruff check app.py`
