# Checklist S9.2 -- POST /portfolio Endpoint

## Implementation Tasks

- [x] `PortfolioRequest` Pydantic model defined (tickers: list[str], min_length=1, max_length=10)
- [x] `POST /api/v1/portfolio` endpoint defined in `api/routes.py`
- [x] Import `PortfolioInsight` from `config.data_contracts`
- [x] Validate each ticker: non-empty after strip, <= 10 chars
- [x] Normalize tickers to uppercase before passing to conductor
- [x] Calls `request.app.state.conductor.analyze_portfolio(tickers)`
- [x] Returns `PortfolioInsight` response model
- [x] Invalid ticker format returns HTTP 400

## Tests

- [x] `test_portfolio_success` -- POST /api/v1/portfolio returns 200 + PortfolioInsight
- [x] `test_portfolio_empty_tickers` -- empty list returns 422
- [x] `test_portfolio_too_many_tickers` -- >10 tickers returns 422
- [x] `test_portfolio_invalid_ticker_format` -- ticker too long returns 400
- [x] `test_portfolio_normalizes_tickers` -- lowercase tickers passed as uppercase
- [x] `test_portfolio_single_ticker` -- single ticker works fine

## Quality

- [x] `ruff check api/routes.py` passes
- [x] `ruff check tests/test_api_routes.py` passes
- [x] All tests pass: `python -m pytest tests/test_api_routes.py -v`
