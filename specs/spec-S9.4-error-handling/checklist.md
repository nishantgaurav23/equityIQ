# Checklist -- Spec S9.4: API Error Taxonomy

## Phase 1: Setup & Dependencies
- [x] Verify S9.1 (analyze endpoint) is implemented and tests pass
- [x] Create `api/exceptions.py`
- [x] Create `api/error_handlers.py`
- [x] Create `tests/test_error_handling.py`

## Phase 2: Tests First (TDD)
- [x] Write test for exception hierarchy (EquityIQError base, 5 subclasses)
- [x] Write test for structured error response schema
- [x] Write test for InvalidTickerError -> 400
- [x] Write test for TickerNotFoundError -> 404
- [x] Write test for AnalysisTimeoutError -> 504
- [x] Write test for InsufficientDataError -> 422
- [x] Write test for VerdictNotFoundError -> 404
- [x] Write test for unhandled exception -> 500 (no traceback leak)
- [x] Write test for portfolio endpoint structured errors
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement `api/exceptions.py` -- EquityIQError base + 5 subclasses
- [x] Implement `api/error_handlers.py` -- FastAPI exception handlers with structured JSON responses
- [x] Wire exception handlers in `app.py` (create_app)
- [x] Update `api/routes.py` -- replace HTTPException with domain exceptions
- [x] Add try/except around conductor calls for timeout handling
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify existing endpoint tests still pass (backward compatibility)
- [x] Run `make local-lint` -- ruff check clean
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] Error responses never leak tracebacks or file paths
- [x] Logging includes appropriate severity (warning for 4xx, error for 5xx)
- [x] Update roadmap.md status: pending -> done
