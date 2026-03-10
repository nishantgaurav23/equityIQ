# S15.1 -- Ticker Search API -- Checklist

## Status: pending

## TDD Checklist

- [ ] **Write tests** (`tests/test_ticker_search.py`)
  - [ ] Test search returns matching tickers with correct fields
  - [ ] Test partial matching works (e.g., "app" -> AAPL)
  - [ ] Test max 8 results enforced
  - [ ] Test minimum query length (1 character)
  - [ ] Test empty query returns empty list
  - [ ] Test results cached with 1hr TTL
  - [ ] Test API failure returns empty list (graceful degradation)
  - [ ] Test Polygon API is mocked (no real HTTP calls)
- [ ] **Implement** (`tools/ticker_search.py`)
  - [ ] Create `search_tickers(query: str)` async function
  - [ ] Call Polygon.io Ticker Search API
  - [ ] Return list of dicts with ticker, name, market, type
  - [ ] Limit results to 8
  - [ ] Add TTLCache with 1hr TTL
  - [ ] Wrap API call in try/except, return [] on failure
- [ ] **Wire endpoint** (`api/routes.py`)
  - [ ] Add `GET /api/v1/search?q={query}` route
  - [ ] Validate query param (min length 1)
  - [ ] Return JSON array of ticker matches
- [ ] **Verify**
  - [ ] All tests pass: `python -m pytest tests/test_ticker_search.py -v`
  - [ ] Ruff clean: `ruff check tools/ticker_search.py api/routes.py`
  - [ ] No hardcoded API keys
