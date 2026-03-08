# S3.1 -- Polygon Connector Checklist

## Setup
- [x] Create `tools/__init__.py`
- [x] Create `tools/polygon_connector.py`
- [x] Create `tests/test_polygon_connector.py`

## Implementation
- [x] `PolygonConnector.__init__` with Settings DI, TTLCache(128, 300), httpx.AsyncClient(timeout=10)
- [x] `get_fundamentals(ticker)` -- /vX/reference/financials, cache, try/except
- [x] `get_price_history(ticker, days)` -- /v2/aggs/ticker/.../range/1/day, cache, try/except
- [x] `get_company_news(ticker, limit)` -- /v2/reference/news, cache, try/except
- [x] `close()` -- aclose the httpx client
- [x] Module-level `polygon = PolygonConnector()` singleton

## Tests
- [x] test_get_fundamentals_success
- [x] test_get_fundamentals_empty
- [x] test_get_fundamentals_error
- [x] test_get_price_history_success
- [x] test_get_price_history_empty
- [x] test_get_price_history_error
- [x] test_get_company_news_success
- [x] test_get_company_news_empty
- [x] test_get_company_news_error
- [x] test_cache_hit
- [x] test_settings_injection
- [x] test_module_singleton
- [x] test_close_method

## Quality
- [x] `ruff check tools/polygon_connector.py` clean
- [x] `pytest tests/test_polygon_connector.py -v` all pass (19/19)
- [x] No hardcoded API keys
