# Spec S3.4 -- SEC Edgar Connector

## Meta
| Field | Value |
|-------|-------|
| Spec ID | S3.4 |
| Phase | 3 -- Data Connectors |
| Depends On | S1.3 (pydantic-settings) |
| Location | `tools/sec_connector.py` |
| Test File | `tests/test_sec_connector.py` |
| Status | spec-written |

## Purpose
Async wrapper for the SEC EDGAR API that retrieves recent SEC filings for a given company (by ticker/CIK) and scores regulatory risk. Used by the ComplianceChecker agent (S7.5) to detect going_concern, restatement, and other risk flags from SEC filings.

## API Surface

### Class: `SecConnector`

#### Constructor
```python
def __init__(self, settings: Settings | None = None) -> None
```
- Uses `config.settings.Settings` for any config (no API key needed -- SEC EDGAR is free)
- Sets `User-Agent` header per SEC requirements (e.g., `"EquityIQ nishantgaurav23@gmail.com"`)
- Creates `httpx.AsyncClient` with 10s timeout
- Creates `TTLCache(maxsize=64, ttl=300)` (5-min TTL)

#### `get_company_cik(ticker: str) -> str | None`
- Fetches CIK number for a ticker from SEC's company tickers JSON
- Caches result
- Returns None on error

#### `get_sec_filings(ticker: str, filing_type: str = "10-K", count: int = 5) -> list[dict]`
- Resolves ticker -> CIK via `get_company_cik()`
- Fetches recent filings from SEC EDGAR EFTS API (`efts.sec.gov/LATEST/search-index`)
  or company submissions API (`data.sec.gov/submissions/CIK{cik}.json`)
- Each filing dict contains:
  - `filing_type`: str (e.g., "10-K", "10-Q", "8-K")
  - `filed_date`: str (ISO date)
  - `description`: str
  - `url`: str (link to filing on SEC)
- Returns `[]` on error
- Results cached with TTL

#### `score_risk(ticker: str) -> dict`
- Fetches recent filings (10-K, 10-Q, 8-K)
- Analyzes filing metadata for risk indicators:
  - `latest_filing_type`: str -- most recent filing type
  - `days_since_filing`: int -- days since most recent filing
  - `risk_flags`: list[str] -- detected risk categories
  - `risk_score`: float [0.0, 1.0] -- overall regulatory risk score
- Risk flag detection logic:
  - "late_filing": days_since_filing > 90 for 10-Q, > 395 for 10-K
  - "going_concern": detected in filing description/text (CRITICAL -- forces SELL)
  - "restatement": detected in filing description/text (CRITICAL -- forces SELL)
  - "sec_investigation": detected in filing description/text
  - "material_weakness": detected in filing description/text
  - "delisting_risk": detected in filing description/text
- Risk score calculation:
  - Base score: 0.1 per risk flag
  - "going_concern" or "restatement": adds 0.5 each
  - Stale filings (days_since_filing > 180): adds 0.2
  - Clamped to [0.0, 1.0]
- Returns `{}` on total failure
- Results cached with TTL

#### `close() -> None`
- Closes the underlying `httpx.AsyncClient`

### Module-level singleton
```python
sec = SecConnector()
```

## Data Flow
```
ComplianceChecker agent
  -> sec.score_risk("AAPL")
    -> get_company_cik("AAPL") -> CIK
    -> get_sec_filings("AAPL") -> list[dict]
    -> analyze filings for risk flags
    -> compute risk_score
  -> returns dict matching ComplianceReport fields
```

## Key Rules
1. **Never crash on API errors** -- all external calls wrapped in try/except, return empty on failure
2. **SEC requires User-Agent header** -- must include app name + email
3. **TTL cache (5 min)** -- all results cached to respect SEC rate limits
4. **going_concern / restatement are CRITICAL** -- these flags drive SELL override in SignalSynthesizer
5. **Risk score clamped [0.0, 1.0]** -- use same clamping pattern as other connectors

## Testing Requirements
- All SEC API calls mocked (httpx responses)
- Test successful filing retrieval with sample SEC response
- Test CIK resolution (success and failure)
- Test risk scoring with various filing scenarios
- Test going_concern and restatement flag detection
- Test cache hits (second call doesn't make HTTP request)
- Test error handling (network error, bad response, timeout)
- Test empty/missing data scenarios
- Test days_since_filing calculation
- Test risk_score clamping to [0.0, 1.0]

## Dependencies
- `httpx` -- async HTTP client
- `cachetools` -- TTL caching
- `config.settings` -- Settings singleton
- `beautifulsoup4` + `lxml` -- HTML parsing (if needed for filing content)
- `datetime` -- date calculations

## Tangible Outcomes
1. `tools/sec_connector.py` exists with `SecConnector` class
2. `tests/test_sec_connector.py` passes all tests
3. `from tools.sec_connector import sec, SecConnector` works
4. `sec.get_sec_filings("AAPL")` returns list of filing dicts
5. `sec.score_risk("AAPL")` returns dict with risk_flags, risk_score
6. All external calls are mocked in tests
7. `ruff check tools/sec_connector.py` passes
