# Spec S9.4 -- API Error Taxonomy

## Overview

Custom exception hierarchy for EquityIQ API endpoints. Defines domain-specific exceptions (TickerNotFoundError, AnalysisTimeoutError, InsufficientDataError) mapped to appropriate HTTP status codes with structured JSON error responses. Replaces ad-hoc HTTPException usage in routes with a consistent error taxonomy.

## Dependencies

| Spec | What It Provides |
|------|-----------------|
| S9.1 | POST /analyze/{ticker} endpoint (existing error handling to refactor) |

## Target Location

- **Exceptions module**: `api/exceptions.py`
- **Exception handlers**: `api/error_handlers.py` (FastAPI exception handlers)
- **App wiring**: `app.py` (register exception handlers)
- **Route updates**: `api/routes.py` (raise domain exceptions instead of HTTPException)
- **Tests**: `tests/test_error_handling.py`

---

## Functional Requirements

### FR-1: Custom Exception Hierarchy
- **What**: Define a base `EquityIQError` and domain-specific subclasses
- **Exceptions**:
  - `EquityIQError(Exception)` -- base class with `message`, `error_code` fields
  - `TickerNotFoundError(EquityIQError)` -- ticker doesn't exist or has no data (HTTP 404)
  - `AnalysisTimeoutError(EquityIQError)` -- agent or analysis pipeline exceeded timeout (HTTP 504)
  - `InsufficientDataError(EquityIQError)` -- not enough data to produce reliable analysis (HTTP 422)
  - `InvalidTickerError(EquityIQError)` -- ticker format is invalid (HTTP 400)
  - `VerdictNotFoundError(EquityIQError)` -- session_id lookup returned nothing (HTTP 404)
- **Each exception** carries: `message` (str), `error_code` (str, e.g. `"TICKER_NOT_FOUND"`), optional `details` (dict)

### FR-2: Structured Error Response
- **What**: All error responses follow a consistent JSON schema
- **Schema**:
  ```json
  {
    "error": {
      "code": "TICKER_NOT_FOUND",
      "message": "Ticker XYZ not found or has no available data",
      "details": {}
    }
  }
  ```
- **Fields**: `code` (uppercase snake_case), `message` (human-readable), `details` (optional extra context)

### FR-3: FastAPI Exception Handlers
- **What**: Register exception handlers on the FastAPI app that catch domain exceptions and return structured responses
- **Mapping**:
  - `InvalidTickerError` -> HTTP 400
  - `InsufficientDataError` -> HTTP 422
  - `TickerNotFoundError` -> HTTP 404
  - `VerdictNotFoundError` -> HTTP 404
  - `AnalysisTimeoutError` -> HTTP 504
  - `EquityIQError` (catch-all for unknown subtypes) -> HTTP 500
- **Logging**: Each handler logs the error at appropriate level (warning for 4xx, error for 5xx)

### FR-4: Route Migration
- **What**: Update `api/routes.py` to raise domain exceptions instead of raw `HTTPException`
- **Changes**:
  - `analyze_ticker`: raise `InvalidTickerError` instead of `HTTPException(400)`
  - `analyze_portfolio`: raise `InvalidTickerError` for bad ticker format
  - `get_verdict`: raise `VerdictNotFoundError` instead of `HTTPException(404)`
  - History endpoints: raise `InvalidTickerError` for empty tickers
- **Catch conductor errors**: Wrap `conductor.analyze()` calls with try/except to catch and re-raise as domain exceptions (e.g., timeout -> `AnalysisTimeoutError`)

### FR-5: Unhandled Exception Safety Net
- **What**: Register a generic Exception handler that returns HTTP 500 with structured response
- **Response**: `{"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {}}}`
- **Logging**: Log full traceback at ERROR level
- **Security**: Never expose internal details (tracebacks, file paths) in response body

---

## Tangible Outcomes

- [ ] **Outcome 1**: `api/exceptions.py` defines 5 custom exceptions inheriting from `EquityIQError`
- [ ] **Outcome 2**: All error responses return structured JSON `{"error": {"code": ..., "message": ..., "details": ...}}`
- [ ] **Outcome 3**: `POST /api/v1/analyze/VERYLONGTICKER` returns 400 with `{"error": {"code": "INVALID_TICKER", ...}}`
- [ ] **Outcome 4**: Conductor timeout raises `AnalysisTimeoutError` -> HTTP 504
- [ ] **Outcome 5**: Unknown verdict session_id returns 404 with `{"error": {"code": "VERDICT_NOT_FOUND", ...}}`
- [ ] **Outcome 6**: Unhandled exceptions return 500 with generic structured error (no traceback leaked)
- [ ] **Outcome 7**: Existing endpoint tests still pass (backward-compatible HTTP status codes)
- [ ] **Outcome 8**: `ruff check api/exceptions.py api/error_handlers.py` clean

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_exception_hierarchy**: All exceptions inherit from `EquityIQError`; each has `message`, `error_code`, `details`
2. **test_error_response_schema**: Error responses match `{"error": {"code": ..., "message": ..., "details": ...}}`
3. **test_invalid_ticker_returns_400**: Invalid ticker format -> 400 with `INVALID_TICKER` code
4. **test_ticker_not_found_returns_404**: `TickerNotFoundError` raised by conductor -> 404 with `TICKER_NOT_FOUND`
5. **test_analysis_timeout_returns_504**: `AnalysisTimeoutError` -> 504 with `ANALYSIS_TIMEOUT`
6. **test_insufficient_data_returns_422**: `InsufficientDataError` -> 422 with `INSUFFICIENT_DATA`
7. **test_verdict_not_found_returns_404**: Missing session_id -> 404 with `VERDICT_NOT_FOUND`
8. **test_unhandled_exception_returns_500**: Random exception -> 500 with `INTERNAL_ERROR`, no traceback in response
9. **test_error_response_has_no_traceback**: 500 responses don't contain stack traces or file paths
10. **test_portfolio_invalid_ticker_structured_error**: Portfolio endpoint with bad ticker returns structured error

### Mocking Strategy
- Mock `conductor.analyze()` to raise various exceptions (asyncio.TimeoutError, ValueError, domain exceptions)
- Use TestClient for endpoint-level testing
- No external services needed (all mocked via app.state)

### Coverage Expectation
- All exception classes tested for correct attributes
- All HTTP status code mappings tested via endpoint calls
- Edge cases: empty details dict, long error messages

---

## References
- roadmap.md -- S9.4 spec row
- api/routes.py -- current endpoint implementation
- FastAPI exception handlers: https://fastapi.tiangolo.com/tutorial/handling-errors/
