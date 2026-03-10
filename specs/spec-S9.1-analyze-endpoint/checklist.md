# Checklist S9.1 -- POST /analyze/{ticker} Endpoint

## Implementation Tasks

- [x] Route file exists: `api/routes.py`
- [x] Router prefix: `/api/v1`
- [x] `POST /analyze/{ticker}` endpoint defined
- [x] Ticker validation: non-empty, <= 10 chars
- [x] Ticker normalization: strip + uppercase
- [x] Calls `request.app.state.conductor.analyze(ticker)`
- [x] Returns `FinalVerdict` response model
- [x] Invalid ticker returns HTTP 400
- [x] Router included in `app.py` via `create_app()`
- [x] `app.py` lifespan initializes `MarketConductor` on `app.state.conductor`

## Tests

- [x] `test_analyze_success` -- POST /api/v1/analyze/AAPL returns 200 + FinalVerdict
- [x] `test_analyze_invalid_ticker` -- too-long ticker returns 400
- [x] `test_analyze_normalizes_ticker` -- lowercase ticker passed as uppercase to conductor

## Quality

- [x] `ruff check api/routes.py` passes
- [x] `ruff check tests/test_api_routes.py` passes
- [x] All tests pass: `python -m pytest tests/test_api_routes.py -v`
