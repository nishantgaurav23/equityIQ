# Checklist -- Spec S3.2: FRED API Async Connector

## Phase 1: Setup & Dependencies
- [x] Verify dependency S1.3 (config/settings.py) is implemented
- [x] Verify `tools/__init__.py` exists
- [x] Confirm FRED_API_KEY field exists in Settings

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_fred_connector.py`
- [x] Write failing tests for `get_macro_indicators` success
- [x] Write failing tests for GDP growth % change calculation
- [x] Write failing tests for inflation rate % change calculation
- [x] Write failing tests for fed_funds_rate direct extraction
- [x] Write failing tests for unemployment_rate direct extraction
- [x] Write failing tests for partial failure (some series fail)
- [x] Write failing tests for total failure (all series fail)
- [x] Write failing tests for FRED "." missing value handling
- [x] Write failing tests for regime classification (4 regimes + None)
- [x] Write failing tests for cache hit behavior
- [x] Write failing tests for settings injection
- [x] Write failing tests for module singleton
- [x] Write failing tests for close method
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement `FredConnector.__init__` with settings, cache, client
- [x] Implement `_fetch_series` with caching and error handling
- [x] Implement `get_macro_indicators` with asyncio.gather
- [x] Implement GDP growth % change calculation
- [x] Implement inflation rate % change calculation
- [x] Implement `_classify_regime` with 4 regime rules
- [x] Implement `close()` method
- [x] Create module-level `fred` singleton
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify `tools/__init__.py` exports are correct
- [x] Run `ruff check tools/fred_connector.py`
- [x] Run `ruff format tools/fred_connector.py`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked (acceptance criteria in spec.md)
- [x] No hardcoded secrets (API key from Settings only)
- [x] All external calls wrapped in try/except
- [x] TTLCache configured (maxsize=64, ttl=3600)
- [x] Update roadmap.md status: pending -> done
