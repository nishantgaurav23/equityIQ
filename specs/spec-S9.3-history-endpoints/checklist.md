# S9.3 History Endpoints -- Checklist

## Test-First (Red)
- [x] Write `test_trend_endpoint_success`
- [x] Write `test_trend_endpoint_empty_ticker`
- [x] Write `test_trend_endpoint_normalizes_ticker`
- [x] Write `test_trend_endpoint_limit_param`
- [x] Write `test_trend_endpoint_default_limit`
- [x] Write `test_trend_endpoint_empty_result`
- [x] Write `test_ticker_history_invalid_ticker`
- [x] Write `test_recent_history_default_params`
- [x] Confirm all new tests fail (red)

## Implementation (Green)
- [x] Import `SignalSnapshot` from `memory.history_retriever` in `api/routes.py`
- [x] Add `GET /api/v1/history/{ticker}/trend` endpoint
- [x] Validate ticker (empty -> HTTPException 400)
- [x] Normalize ticker to uppercase
- [x] Call `history_retriever.get_signal_trend(ticker, limit=limit)`
- [x] Return `list[SignalSnapshot]` with `response_model`
- [x] All tests pass (green)

## Quality (Refactor)
- [x] `ruff check api/routes.py` clean
- [x] `ruff check tests/test_api_routes.py` clean
- [x] No import order issues

## Verification
- [x] All outcomes from spec.md satisfied
- [x] `python -m pytest tests/test_api_routes.py -v` all pass (23/23)
- [x] Endpoint registered in router (visible in OpenAPI docs)
- [x] roadmap.md updated to `done`
