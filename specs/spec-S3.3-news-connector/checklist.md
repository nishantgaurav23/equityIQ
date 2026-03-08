# Checklist -- Spec S3.3: NewsAPI Async Connector + Sentiment Scoring

## Phase 1: Setup & Dependencies
- [x] Verify dependency S1.3 (config/settings.py) is implemented
- [x] Verify `tools/__init__.py` exists
- [x] Confirm NEWS_API_KEY field exists in Settings

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_news_connector.py`
- [x] Write failing tests for `get_news_sentiment` success
- [x] Write failing tests for sentiment scoring (positive, negative, neutral, mixed)
- [x] Write failing tests for event detection (earnings, multiple, none)
- [x] Write failing tests for top headlines limited to 5
- [x] Write failing tests for total failure (API error)
- [x] Write failing tests for empty results
- [x] Write failing tests for cache hit behavior
- [x] Write failing tests for settings injection
- [x] Write failing tests for module singleton
- [x] Write failing tests for close method
- [x] Write failing tests for _score_text edge cases (empty, None)
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement `NewsConnector.__init__` with settings, cache, client
- [x] Implement `_fetch_articles` with caching and error handling
- [x] Implement `_score_text` with keyword matching
- [x] Implement `_detect_events` with event keyword scanning
- [x] Implement `get_news_sentiment` with sentiment aggregation
- [x] Implement `close()` method
- [x] Create module-level `news` singleton
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify `tools/__init__.py` exports are correct
- [x] Run `ruff check tools/news_connector.py`
- [x] Run `ruff format tools/news_connector.py`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked (acceptance criteria in spec.md)
- [x] No hardcoded secrets (API key from Settings only)
- [x] All external calls wrapped in try/except
- [x] TTLCache configured (maxsize=64, ttl=300)
- [x] Update roadmap.md status: pending -> done
