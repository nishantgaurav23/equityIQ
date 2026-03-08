# Checklist S3.4 -- SEC Edgar Connector

## Implementation Tasks

- [x] Create `tools/sec_connector.py` with `SecConnector` class
- [x] Implement `__init__` with Settings, httpx.AsyncClient, TTLCache(5min), User-Agent header
- [x] Implement `get_company_cik(ticker)` -- resolve ticker to CIK number
- [x] Implement `get_sec_filings(ticker, filing_type, count)` -- fetch recent filings
- [x] Implement `score_risk(ticker)` -- analyze filings for risk flags + score
- [x] Implement risk flag detection (going_concern, restatement, late_filing, etc.)
- [x] Implement risk_score calculation with proper weighting and clamping
- [x] Implement `close()` method
- [x] Add module-level singleton `sec = SecConnector()`
- [x] Ensure all external calls wrapped in try/except

## Testing Tasks

- [x] Create `tests/test_sec_connector.py`
- [x] Test CIK resolution (success case)
- [x] Test CIK resolution (failure / not found)
- [x] Test get_sec_filings success with mocked SEC response
- [x] Test get_sec_filings with network error returns []
- [x] Test score_risk with clean filings (low risk)
- [x] Test score_risk with going_concern flag (high risk)
- [x] Test score_risk with restatement flag (high risk)
- [x] Test score_risk with late filings
- [x] Test score_risk with multiple risk flags
- [x] Test score_risk with empty filings returns {}
- [x] Test TTL cache hit (no duplicate HTTP call)
- [x] Test risk_score clamped to [0.0, 1.0]
- [x] All tests pass: `python -m pytest tests/test_sec_connector.py -v` (25/25)

## Quality Gates

- [x] `ruff check tools/sec_connector.py` -- no errors
- [x] `ruff check tests/test_sec_connector.py` -- no errors
- [x] No hardcoded API keys
- [x] Follows async patterns from other connectors (fred, news, polygon)
