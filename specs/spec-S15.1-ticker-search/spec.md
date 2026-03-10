# S15.1 -- Ticker Search API

## Feature
Ticker search/autocomplete endpoint.

## Location
- `tools/ticker_search.py`
- `api/routes.py`

## Depends On
- S1.3 (settings)
- S3.1 (polygon connector)

## Description
Add `GET /api/v1/search?q={query}` endpoint that resolves company names to ticker symbols
using Polygon.io's Ticker Search API. Returns top 8 matches with ticker, company name,
market, type. Supports partial matching ("app" -> AAPL Apple Inc). Caches results with
1hr TTL. Falls back to empty list on API failure.

## Acceptance Criteria

1. `GET /api/v1/search?q=apple` returns `[{ticker: "AAPL", name: "Apple Inc", market: "stocks", type: "CS"}, ...]`
2. Results cached with 1hr TTL via `cachetools`
3. Returns empty list on API failure (never crashes)
4. Max 8 results returned
5. Minimum query length: 1 character
6. Tests mock Polygon API and verify search, caching, error handling
