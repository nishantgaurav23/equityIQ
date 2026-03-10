# S17.2 -- Alpaca Integration Checklist

## Settings & Config
- [x] Add ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_BASE_URL, ALPACA_DATA_URL to settings.py
- [x] Add ALPACA_ALLOW_PAPER_TRADING to settings.py
- [x] Settings test: verify new fields load from env

## Data Models
- [x] AlpacaPosition Pydantic model in integrations/alpaca.py
- [x] AlpacaAccount Pydantic model
- [x] AlpacaOrder Pydantic model
- [x] AlpacaPortfolio Pydantic model
- [x] Model validation tests

## Symbol Mapping
- [x] map_alpaca_to_equityiq() -- US stocks pass through
- [x] map_equityiq_to_alpaca() -- strip suffixes, reject Indian tickers
- [x] Handle edge cases (class B shares, etc.)
- [x] Symbol mapping tests

## Core API Client
- [x] AlpacaClient class with httpx.AsyncClient
- [x] Auth headers construction (APCA-API-KEY-ID, APCA-API-SECRET-KEY)
- [x] get_account() fetches and parses account info
- [x] get_positions() fetches and parses positions
- [x] get_portfolio_summary() aggregates data
- [x] place_paper_order() with safety checks
- [x] TTL cache on positions/account (15s)
- [x] All external calls wrapped in try/except
- [x] Client tests with mocked responses

## API Endpoints
- [x] GET /api/v1/alpaca/account
- [x] GET /api/v1/alpaca/positions
- [x] GET /api/v1/alpaca/portfolio
- [x] POST /api/v1/alpaca/analyze
- [x] POST /api/v1/alpaca/paper-order
- [x] Route tests (FastAPI TestClient)

## Error Handling
- [x] 401 handling (invalid credentials)
- [x] 403 handling (forbidden)
- [x] 429 handling (rate limit)
- [x] Network error handling (timeout, connection error)
- [x] Error response tests

## Safety Checks
- [x] Live trading blocked (hard-coded check)
- [x] Paper orders gated behind ALPACA_ALLOW_PAPER_TRADING
- [x] Safety check tests

## Integration
- [x] Alpaca router mounted in app.py
- [x] All tests pass: pytest tests/test_alpaca.py -v
- [x] Lint clean: ruff check integrations/alpaca.py api/alpaca_routes.py tests/test_alpaca.py
