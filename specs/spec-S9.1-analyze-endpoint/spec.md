# Spec S9.1 -- POST /analyze/{ticker} Endpoint

## Overview

FastAPI endpoint that accepts a stock ticker, orchestrates the full multi-agent analysis pipeline via MarketConductor, and returns a FinalVerdict JSON response.

## Location

- **Route file**: `api/routes.py`
- **App wiring**: `app.py` (includes router)
- **Tests**: `tests/test_api_routes.py`

## Dependencies

| Spec | What It Provides |
|------|-----------------|
| S8.2 | MarketConductor.analyze(ticker) -> FinalVerdict |
| S1.4 | FastAPI app factory with lifespan, router inclusion |

## Endpoint Specification

### `POST /api/v1/analyze/{ticker}`

**Path Parameter:**
- `ticker` (str): Stock ticker symbol (e.g., AAPL, TSLA, MSFT)

**Request Validation:**
- Ticker must be non-empty after stripping whitespace
- Ticker must be <= 10 characters (rejects overly long inputs)
- Ticker is normalized to uppercase before processing

**Response:**
- Status 200: `FinalVerdict` JSON (see config/data_contracts.py)
- Status 400: Invalid ticker format
- Status 500: Internal server error (unhandled exceptions)

**Response Schema (FinalVerdict):**
```json
{
  "ticker": "AAPL",
  "final_signal": "BUY",
  "overall_confidence": 0.75,
  "price_target": null,
  "analyst_signals": {"ValuationScout": "BUY", ...},
  "risk_summary": "",
  "key_drivers": ["Strong fundamentals", ...],
  "session_id": "uuid-string",
  "timestamp": "2026-03-09T12:00:00Z"
}
```

**Processing Flow:**
1. Validate ticker format
2. Normalize ticker to uppercase
3. Call `request.app.state.conductor.analyze(ticker)`
4. Return FinalVerdict JSON (conductor handles storage in InsightVault)

**Timeout:**
- Individual agents have 30s timeout (managed by MarketConductor)
- Overall endpoint should respond within 60s (handled at infrastructure level)

## Integration Points

- `app.py` lifespan initializes `MarketConductor` on `app.state.conductor`
- Router mounted at `/api/v1` prefix via `app.include_router()`
- MarketConductor handles all agent orchestration, signal fusion, and verdict storage

## Non-Goals (This Spec)

- Custom error taxonomy (S9.4)
- Portfolio analysis endpoint (S9.2)
- History endpoints (S9.3 -- though already implemented alongside)

## Tangible Outcomes

1. `POST /api/v1/analyze/AAPL` returns 200 with valid FinalVerdict JSON
2. Invalid tickers return 400
3. Ticker is normalized to uppercase
4. All tests in `tests/test_api_routes.py::TestAnalyzeEndpoint` pass
5. `ruff check api/routes.py` clean
