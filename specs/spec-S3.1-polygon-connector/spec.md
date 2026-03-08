# S3.1 -- Polygon.io Async Connector

## Metadata

| Field | Value |
|-------|-------|
| Spec ID | S3.1 |
| Phase | 3 -- Data Connectors |
| Depends On | S1.3 (config/settings.py -- POLYGON_API_KEY) |
| Location | `tools/polygon_connector.py` |
| Test File | `tests/test_polygon_connector.py` |
| Status | spec-written |

## Purpose

Async wrapper around the Polygon.io REST API. Provides three functions consumed by downstream agents:

- **ValuationScout** calls `get_fundamentals(ticker)` for financial ratios
- **MomentumTracker** calls `get_price_history(ticker, days)` for OHLCV data
- **PulseMonitor** calls `get_company_news(ticker, limit)` for recent headlines
- **RiskGuardian** calls `get_price_history(ticker, days=365)` for volatility/drawdown

## API Endpoints Used

| Function | Polygon Endpoint | Notes |
|----------|-----------------|-------|
| `get_fundamentals` | `GET /vX/reference/financials?ticker={}&limit=1` | Returns latest filing |
| `get_price_history` | `GET /v2/aggs/ticker/{}/range/1/day/{from}/{to}` | Daily OHLCV bars, adjusted, ascending |
| `get_company_news` | `GET /v2/reference/news?ticker={}&limit={}` | Recent news articles |

## Interface

```python
class PolygonConnector:
    """Async Polygon.io API wrapper with TTL caching."""

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize with settings (dependency injection for testing).
        Falls back to get_settings() if not provided.
        - self.api_key: from settings.POLYGON_API_KEY
        - self.base_url: "https://api.polygon.io"
        - self.cache: TTLCache(maxsize=128, ttl=300)  # 5-minute TTL
        - self.client: httpx.AsyncClient(timeout=10.0)
        """

    async def get_fundamentals(self, ticker: str) -> dict:
        """
        Fetch latest financial ratios for ticker.
        Returns: {"pe_ratio": float|None, "pb_ratio": float|None,
                  "revenue_growth": float|None, "debt_to_equity": float|None,
                  "fcf_yield": float|None}
        Returns {} on error or missing data.
        Cache key: f"fundamentals_{ticker}"
        """

    async def get_price_history(self, ticker: str, days: int = 90) -> dict:
        """
        Fetch daily OHLCV bars for the last N days.
        Returns: {"prices": list[float], "volumes": list[float], "dates": list[str]}
        Prices are adjusted close. Dates as "YYYY-MM-DD". Sorted oldest->newest.
        Returns {} on error or no data.
        Cache key: f"price_{ticker}_{days}"
        """

    async def get_company_news(self, ticker: str, limit: int = 10) -> dict:
        """
        Fetch recent news articles for ticker.
        Returns: {"headlines": list[str], "articles": list[dict]}
        Each article: {"title": str, "published_utc": str}
        Returns {} on error or no data.
        Cache key: f"news_{ticker}"
        """

    async def close(self) -> None:
        """Close the underlying httpx client."""

# Module-level singleton
polygon: PolygonConnector
```

## Design Decisions

1. **Dependency injection**: `__init__` accepts optional `Settings` for testability. Falls back to `get_settings()`.
2. **TTLCache 5 min (300s)**: Polygon free tier is 5 req/min. Caching prevents rate limit exhaustion.
3. **`httpx.AsyncClient`**: Shared client with connection pooling. 10s timeout.
4. **Never crash**: Every external call wrapped in `try/except Exception`. Returns `{}` on failure.
5. **Module singleton**: `polygon = PolygonConnector()` at module bottom for simple imports.
6. **`close()` method**: For graceful cleanup during app shutdown (lifespan hook).

## Constraints

- All functions are `async def`.
- API key sourced from `config.settings.get_settings().POLYGON_API_KEY` -- never hardcoded.
- Cache TTL is 300 seconds (5 minutes). `maxsize=128`.
- `httpx.AsyncClient` timeout is 10 seconds.
- Return `{}` (empty dict) on any error -- never raise to caller.
- Dates formatted as `"YYYY-MM-DD"`.
- Price history sorted ascending (oldest first).
- All API calls include `apiKey` as query parameter.

## Test Requirements

All tests must mock `httpx.AsyncClient` -- no real network calls.

1. **Fundamentals**: Mock successful response, assert returned dict has expected keys.
2. **Fundamentals empty**: Mock empty results, assert `{}`.
3. **Fundamentals error**: Mock exception, assert `{}`.
4. **Price history**: Mock bars response, assert prices/volumes/dates lists correct.
5. **Price history empty**: Mock no results, assert `{}`.
6. **Price history error**: Mock exception, assert `{}`.
7. **Company news**: Mock articles response, assert headlines/articles correct.
8. **Company news empty**: Mock no results, assert `{}`.
9. **Company news error**: Mock exception, assert `{}`.
10. **Cache hit**: Call twice, assert HTTP called only once.
11. **Settings injection**: Confirm API key from settings used in requests.
12. **Module singleton**: `from tools.polygon_connector import polygon` works.
13. **Close method**: `await polygon.close()` calls `client.aclose()`.

## Acceptance Criteria

- [ ] `tools/polygon_connector.py` exists with `PolygonConnector` class
- [ ] `tools/__init__.py` exists (package init)
- [ ] Three async methods: `get_fundamentals`, `get_price_history`, `get_company_news`
- [ ] `close()` async method for client cleanup
- [ ] TTLCache with maxsize=128, ttl=300
- [ ] httpx.AsyncClient with timeout=10.0
- [ ] API key from Settings (dependency injection)
- [ ] All external calls wrapped in try/except
- [ ] Returns {} on any error
- [ ] Module-level `polygon` singleton
- [ ] All tests pass (`pytest tests/test_polygon_connector.py -v`)
- [ ] Ruff clean (`ruff check tools/polygon_connector.py`)
