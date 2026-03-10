# Spec S9.2 -- POST /portfolio Endpoint

## Overview

FastAPI endpoint that accepts a list of stock tickers (max 10), orchestrates multi-stock analysis via MarketConductor.analyze_portfolio(), and returns a PortfolioInsight JSON response.

## Location

- **Route file**: `api/routes.py`
- **App wiring**: `app.py` (router already included)
- **Tests**: `tests/test_api_routes.py`

## Dependencies

| Spec | What It Provides |
|------|-----------------|
| S8.3 | MarketConductor.analyze_portfolio(tickers) -> PortfolioInsight |
| S1.4 | FastAPI app factory with lifespan, router inclusion |

## Endpoint Specification

### `POST /api/v1/portfolio`

**Request Body (JSON):**
```json
{
  "tickers": ["AAPL", "TSLA", "MSFT"]
}
```

**Request Validation:**
- `tickers` must be a non-empty list
- Maximum 10 tickers allowed (returns 400 if exceeded)
- Each ticker must be non-empty after stripping whitespace
- Each ticker must be <= 10 characters
- Tickers are normalized to uppercase before processing
- Duplicate tickers are accepted (MarketConductor deduplicates)

**Request Model (Pydantic):**
```python
class PortfolioRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, max_length=10)
```

**Response:**
- Status 200: `PortfolioInsight` JSON (see config/data_contracts.py)
- Status 400: Invalid request (empty tickers, too many tickers, invalid ticker format)
- Status 422: Validation error (missing field, wrong type)
- Status 500: Internal server error

**Response Schema (PortfolioInsight):**
```json
{
  "tickers": ["AAPL", "TSLA", "MSFT"],
  "verdicts": [...],
  "portfolio_signal": "BUY",
  "diversification_score": 0.65,
  "top_pick": "AAPL",
  "timestamp": "2026-03-09T12:00:00Z"
}
```

**Processing Flow:**
1. Validate request body (Pydantic handles structure)
2. Validate each ticker format (non-empty, <= 10 chars)
3. Normalize tickers to uppercase
4. Call `request.app.state.conductor.analyze_portfolio(tickers)`
5. Return PortfolioInsight JSON

## Integration Points

- MarketConductor already initialized on `app.state.conductor` (from S9.1 lifespan)
- Router already mounted at `/api/v1` prefix
- PortfolioInsight schema already defined in config/data_contracts.py

## Non-Goals (This Spec)

- Custom error taxonomy (S9.4)
- History endpoints (S9.3)
- Portfolio persistence/tracking over time

## Tangible Outcomes

1. `POST /api/v1/portfolio` with valid tickers returns 200 with valid PortfolioInsight JSON
2. Empty tickers list returns 422 (Pydantic validation)
3. More than 10 tickers returns 422 (Pydantic max_length)
4. Invalid ticker format (too long) returns 400
5. Tickers are normalized to uppercase
6. All tests in `tests/test_api_routes.py::TestPortfolioEndpoint` pass
7. `ruff check api/routes.py` clean
