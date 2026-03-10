# S17.1 -- Zerodha Integration Checklist

## Settings & Config
- [x] Add ZERODHA_API_KEY, ZERODHA_API_SECRET, ZERODHA_REDIRECT_URL to settings.py
- [x] Settings test: verify new fields load from env

## Data Models
- [x] ZerodhaHolding Pydantic model in integrations/zerodha.py
- [x] ZerodhaPosition Pydantic model
- [x] ZerodhaPortfolio Pydantic model
- [x] Model validation tests (clamping, required fields)

## Symbol Mapping
- [x] map_zerodha_to_equityiq() -- NSE->".NS", BSE->".BO"
- [x] map_equityiq_to_zerodha() -- reverse mapping
- [x] Handle edge cases (non-equity, special symbols)
- [x] Symbol mapping tests

## OAuth2 Flow
- [x] get_login_url() returns correct Kite Connect URL
- [x] exchange_request_token() exchanges token via Kite API
- [x] Token expiry tracking
- [x] OAuth2 flow tests (mocked)

## Core API Client
- [x] ZerodhaClient class with httpx.AsyncClient
- [x] get_holdings() fetches and parses holdings
- [x] get_positions() fetches and parses positions
- [x] get_portfolio_summary() aggregates data
- [x] TTL cache on holdings/positions (30s)
- [x] Rate limiting (3 req/s semaphore)
- [x] All external calls wrapped in try/except
- [x] Client tests with mocked responses

## API Endpoints
- [x] GET /api/v1/zerodha/login
- [x] GET /api/v1/zerodha/callback
- [x] GET /api/v1/zerodha/holdings
- [x] GET /api/v1/zerodha/positions
- [x] GET /api/v1/zerodha/portfolio
- [x] POST /api/v1/zerodha/analyze
- [x] Route tests (FastAPI TestClient)

## Error Handling
- [x] TokenException handling (401 response)
- [x] NetworkException handling (timeout, connection error)
- [x] Invalid response handling
- [x] Error response tests

## Integration
- [x] integrations/__init__.py created
- [x] Zerodha router mounted in app.py
- [x] All tests pass: pytest tests/test_zerodha.py -v
- [x] Lint clean: ruff check integrations/ tests/test_zerodha.py
