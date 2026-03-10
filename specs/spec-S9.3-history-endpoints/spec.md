# Spec S9.3 -- History Endpoints

## Overview

GET endpoints for retrieving past analysis verdicts and signal trends. Exposes HistoryRetriever (S5.2) data through the FastAPI API layer, enabling clients to view analysis history and visualize signal evolution over time.

## Location

- **Route file**: `api/routes.py` (add to existing router)
- **App wiring**: `app.py` (already includes router, already initializes `history_retriever` on `app.state`)
- **Tests**: `tests/test_api_routes.py` (extend with `TestHistoryEndpointsS93`)

## Dependencies

| Spec | What It Provides |
|------|-----------------|
| S5.2 | HistoryRetriever with `get_ticker_history()`, `get_signal_trend()`, `get_recent_verdicts()` + SignalSnapshot model |
| S1.4 | FastAPI app factory with lifespan, router inclusion |

---

## Endpoint Specifications

### `GET /api/v1/history/{ticker}`

**Already exists** (added alongside S9.1). Returns past verdicts for a specific ticker.

- **Path param**: `ticker` (str) -- stock ticker symbol
- **Query params**: `limit` (int, default=20, 1-200), `offset` (int, default=0, >=0)
- **Response 200**: `list[FinalVerdict]` -- ordered newest first
- **Response 400**: Empty/invalid ticker
- **Processing**: Normalize ticker to uppercase, call `history_retriever.get_ticker_history()`

### `GET /api/v1/history/{ticker}/trend`

**NEW endpoint**. Returns signal trend data showing how the signal evolved over time.

- **Path param**: `ticker` (str) -- stock ticker symbol
- **Query params**: `limit` (int, default=20, 1-100)
- **Response 200**: `list[SignalSnapshot]` -- ordered chronologically (oldest first)
  ```json
  [
    {
      "session_id": "uuid-1",
      "ticker": "AAPL",
      "final_signal": "HOLD",
      "overall_confidence": 0.65,
      "created_at": "2026-03-01T10:00:00Z"
    },
    {
      "session_id": "uuid-2",
      "ticker": "AAPL",
      "final_signal": "BUY",
      "overall_confidence": 0.72,
      "created_at": "2026-03-05T10:00:00Z"
    }
  ]
  ```
- **Response 400**: Empty/invalid ticker
- **Processing**: Normalize ticker to uppercase, call `history_retriever.get_signal_trend()`

### `GET /api/v1/history`

**Already exists** (added alongside S9.1). Returns recent verdicts across all tickers.

- **Query params**: `limit` (int, default=20, 1-200), `offset` (int, default=0, >=0)
- **Response 200**: `list[FinalVerdict]` -- ordered newest first
- **Processing**: Call `history_retriever.get_recent_verdicts()`

---

## Functional Requirements

### FR-1: Signal trend endpoint
- Add `GET /api/v1/history/{ticker}/trend` to `api/routes.py`
- Validates ticker (non-empty after strip)
- Normalizes ticker to uppercase
- Returns `list[SignalSnapshot]` from `history_retriever.get_signal_trend()`
- Query param `limit` (default=20, ge=1, le=100)

### FR-2: Import SignalSnapshot
- Import `SignalSnapshot` from `memory.history_retriever` in `api/routes.py`
- Use as response_model for trend endpoint

### FR-3: Comprehensive test coverage
- Tests for all three history endpoints (ticker history, trend, recent)
- Tests for validation (empty ticker -> 400)
- Tests for query parameter passing (limit, offset)
- Tests for the new trend endpoint specifically

---

## Tangible Outcomes

- [ ] **Outcome 1**: `GET /api/v1/history/{ticker}/trend` endpoint exists and returns `list[SignalSnapshot]`
- [ ] **Outcome 2**: Trend endpoint validates ticker (empty -> 400) and normalizes to uppercase
- [ ] **Outcome 3**: Trend endpoint passes `limit` query param to `get_signal_trend()`
- [ ] **Outcome 4**: All existing history endpoints still function correctly
- [ ] **Outcome 5**: Comprehensive tests in `TestHistoryEndpointsS93` class
- [ ] **Outcome 6**: `ruff check api/routes.py` clean
- [ ] **Outcome 7**: All tests pass: `python -m pytest tests/test_api_routes.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_trend_endpoint_success**: Mock `get_signal_trend` returning snapshots, verify 200 + correct data
2. **test_trend_endpoint_empty_ticker**: Ensure empty ticker returns 400
3. **test_trend_endpoint_normalizes_ticker**: Verify ticker passed uppercase to retriever
4. **test_trend_endpoint_limit_param**: Verify limit query param passed through
5. **test_trend_endpoint_default_limit**: Verify default limit=20 used when not specified
6. **test_trend_endpoint_empty_result**: Mock returning empty list, verify 200 + empty array
7. **test_ticker_history_invalid_ticker**: Empty ticker returns 400
8. **test_recent_history_default_params**: Default limit/offset work correctly

### Mocking Strategy
- Mock `app.state.history_retriever` methods with `AsyncMock`
- Use `SignalSnapshot` model for mock return values in trend tests
- Reuse existing `app` fixture from test_api_routes.py

### Coverage Expectation
- All three history endpoints have happy-path and edge-case tests
- Focus on the new trend endpoint since existing endpoints already have basic tests

---

## References
- roadmap.md -- S9.3 row
- api/routes.py -- existing history endpoints
- memory/history_retriever.py -- HistoryRetriever, SignalSnapshot
- config/data_contracts.py -- FinalVerdict schema
