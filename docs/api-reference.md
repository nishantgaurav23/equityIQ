# API Reference

EquityIQ exposes a REST API via FastAPI. All endpoints are prefixed with `/api/v1` unless noted.

Base URL: `http://localhost:8000` (local dev) or your Cloud Run URL (production).

---

## Health Check

### `GET /health`

Liveness/readiness probe.

```bash
curl http://localhost:8000/health
```

**Response (200):**

```json
{
  "status": "ok",
  "environment": "local",
  "version": "0.1.0"
}
```

---

## Analyze Ticker

### `POST /api/v1/analyze/{ticker}`

Run full multi-agent analysis on a stock ticker. Orchestrates all 6 specialist agents in parallel, fuses signals via XGBoost, applies compliance overrides, and returns a 5-level FinalVerdict.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `ticker` | string | Stock ticker symbol (e.g., AAPL, RELIANCE.NS) |

```bash
curl -X POST http://localhost:8000/api/v1/analyze/AAPL
```

**Response (200):**

```json
{
  "ticker": "AAPL",
  "final_signal": "BUY",
  "overall_confidence": 0.72,
  "price_target": 195.50,
  "analyst_signals": {
    "valuation_scout": "BUY",
    "momentum_tracker": "BUY",
    "pulse_monitor": "HOLD",
    "economy_watcher": "HOLD",
    "compliance_checker": "BUY"
  },
  "risk_summary": {
    "beta": 1.2,
    "annualized_volatility": 0.28,
    "suggested_position_size": 0.08
  },
  "key_drivers": ["Strong revenue growth", "Positive momentum"],
  "session_id": "a1b2c3d4-...",
  "timestamp": "2026-03-10T12:00:00Z"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid ticker (empty or > 20 chars) |
| 408 | Analysis timed out |
| 500 | Internal server error |

---

## Portfolio Analysis

### `POST /api/v1/portfolio`

Analyze a portfolio of up to 10 tickers in parallel.

**Request Body:**

```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT"]
}
```

```bash
curl -X POST http://localhost:8000/api/v1/portfolio \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "GOOGL", "MSFT"]}'
```

**Response (200):**

```json
{
  "tickers": ["AAPL", "GOOGL", "MSFT"],
  "verdicts": [...],
  "portfolio_signal": "BUY",
  "diversification_score": 0.65,
  "top_pick": "AAPL"
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Empty tickers list or invalid ticker |
| 408 | Analysis timed out |
| 422 | Validation error (missing body, > 10 tickers) |

---

## History Endpoints

### `GET /api/v1/history/{ticker}`

Retrieve past analysis verdicts for a specific ticker.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Max results (1-200) |
| `offset` | int | 0 | Pagination offset |

```bash
curl "http://localhost:8000/api/v1/history/AAPL?limit=5"
```

**Response (200):** Array of `FinalVerdict` objects.

---

### `GET /api/v1/history`

Retrieve most recent verdicts across all tickers.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Max results (1-200) |
| `offset` | int | 0 | Pagination offset |

```bash
curl "http://localhost:8000/api/v1/history?limit=10"
```

---

### `GET /api/v1/history/{ticker}/trend`

Retrieve signal trend data for a ticker (oldest first).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 20 | Max results (1-100) |

```bash
curl "http://localhost:8000/api/v1/history/AAPL/trend?limit=30"
```

---

### `GET /api/v1/verdict/{session_id}`

Retrieve a specific verdict by session ID.

```bash
curl http://localhost:8000/api/v1/verdict/a1b2c3d4-5678-...
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 404 | Verdict not found for given session_id |

---

## Search

### `GET /api/v1/search`

Search for tickers by company name or symbol. Supports US, India, and global markets via Yahoo Finance with Polygon fallback.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | "" | Search query |
| `market` | string | "all" | Filter: "us", "in", "all" |

```bash
curl "http://localhost:8000/api/v1/search?q=apple&market=us"
```

**Response (200):**

```json
[
  {
    "ticker": "AAPL",
    "name": "Apple Inc.",
    "locale": "us",
    "exchange": "NASDAQ"
  }
]
```

---

## Price History

### `GET /api/v1/price-history/{ticker}`

Fetch daily OHLCV price history via Yahoo Finance (with Polygon fallback for US tickers).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 90 | History period (1-365) |

```bash
curl "http://localhost:8000/api/v1/price-history/AAPL?days=30"
```

---

### `GET /api/v1/price-history-multi`

Fetch price history for multiple tickers at once.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tickers` | string | Comma-separated ticker symbols (max 10) |
| `days` | int | History period (1-365, default 90) |

```bash
curl "http://localhost:8000/api/v1/price-history-multi?tickers=AAPL,GOOGL&days=60"
```

---

### `GET /api/v1/exchange-rate`

Get exchange rate between two currencies.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_currency` | string | "USD" | Source currency |
| `to_currency` | string | "INR" | Target currency |

```bash
curl "http://localhost:8000/api/v1/exchange-rate?from_currency=USD&to_currency=INR"
```

---

## Agents

### `GET /api/v1/agents`

List all available specialist agents and their status.

```bash
curl http://localhost:8000/api/v1/agents
```

**Response (200):**

```json
[
  {
    "name": "ValuationScout",
    "status": "available",
    "card": { ... }
  }
]
```

---

## Interactive API Docs

FastAPI auto-generates interactive documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
