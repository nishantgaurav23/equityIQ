# S3.2 -- FRED API Async Connector

## Metadata

| Field | Value |
|-------|-------|
| Spec ID | S3.2 |
| Phase | 3 -- Data Connectors |
| Depends On | S1.3 (config/settings.py -- FRED_API_KEY) |
| Location | `tools/fred_connector.py` |
| Test File | `tests/test_fred_connector.py` |
| Status | spec-written |

## Purpose

Async wrapper around the FRED (Federal Reserve Economic Data) REST API. Provides macro indicator data consumed by the **EconomyWatcher** agent (port 8004) to populate `EconomyReport` fields: `gdp_growth`, `inflation_rate`, `fed_funds_rate`, `unemployment_rate`, and `macro_regime`.

## API Endpoints Used

| Function | FRED Endpoint | Series IDs | Notes |
|----------|--------------|------------|-------|
| `get_macro_indicators` | `GET /fred/series/observations` | GDP, CPIAUCSL, FEDFUNDS, UNRATE | One request per series. Returns latest observation value |

FRED series mapping:

| Indicator | Series ID | Unit | Frequency |
|-----------|-----------|------|-----------|
| GDP Growth (annualized %) | `GDP` | Billions $, compute % change | Quarterly |
| Inflation Rate (CPI YoY %) | `CPIAUCSL` | Index, compute YoY % change | Monthly |
| Fed Funds Rate (%) | `FEDFUNDS` | % | Monthly |
| Unemployment Rate (%) | `UNRATE` | % | Monthly |

## Interface

```python
class FredConnector:
    """Async FRED API wrapper with TTL caching."""

    SERIES_MAP: dict[str, str] = {
        "gdp_growth": "GDP",
        "inflation_rate": "CPIAUCSL",
        "fed_funds_rate": "FEDFUNDS",
        "unemployment_rate": "UNRATE",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize with settings (dependency injection for testing).
        Falls back to get_settings() if not provided.
        - self.api_key: from settings.FRED_API_KEY
        - self.base_url: "https://api.stlouisfed.org"
        - self.cache: TTLCache(maxsize=64, ttl=3600)  # 1-hour TTL
        - self.client: httpx.AsyncClient(timeout=10.0)
        """

    async def _fetch_series(self, series_id: str, limit: int = 2) -> list[dict]:
        """
        Fetch the latest observations for a FRED series.
        URL: {base_url}/fred/series/observations?series_id={}&api_key={}&file_type=json&sort_order=desc&limit={}
        Returns list of observation dicts: [{"date": str, "value": str}, ...]
        Returns [] on error.
        Cache key: f"fred_{series_id}"
        """

    async def get_macro_indicators(self) -> dict:
        """
        Fetch all 4 macro indicators in parallel (asyncio.gather).
        Returns: {
            "gdp_growth": float | None,       # YoY % change from last 2 GDP observations
            "inflation_rate": float | None,    # Latest CPI YoY % change (approximated from last 2)
            "fed_funds_rate": float | None,    # Latest value directly
            "unemployment_rate": float | None, # Latest value directly
            "macro_regime": str | None,        # "expansion" | "contraction" | "stagflation" | "recovery"
        }
        Returns {} on total failure.
        Cache key: "macro_indicators"
        """

    def _classify_regime(
        self,
        gdp_growth: float | None,
        inflation_rate: float | None,
        unemployment_rate: float | None,
    ) -> str | None:
        """
        Classify macro regime based on indicators:
        - expansion: gdp_growth > 2.0 AND inflation_rate < 4.0
        - contraction: gdp_growth < 0.0
        - stagflation: gdp_growth < 2.0 AND inflation_rate > 4.0
        - recovery: gdp_growth > 0.0 AND gdp_growth <= 2.0 AND inflation_rate <= 4.0
        Returns None if insufficient data.
        """

    async def close(self) -> None:
        """Close the underlying httpx client."""

# Module-level singleton
fred: FredConnector
```

## Design Decisions

1. **Dependency injection**: `__init__` accepts optional `Settings` for testability. Falls back to `get_settings()`.
2. **TTLCache 1 hour (3600s)**: FRED data updates infrequently (monthly/quarterly). 1-hour cache avoids redundant calls.
3. **`httpx.AsyncClient`**: Shared client with connection pooling. 10s timeout.
4. **Never crash**: Every external call wrapped in `try/except Exception`. Returns `{}` on failure.
5. **Module singleton**: `fred = FredConnector()` at module bottom for simple imports.
6. **`close()` method**: For graceful cleanup during app shutdown (lifespan hook).
7. **Parallel fetching**: `get_macro_indicators` uses `asyncio.gather` to fetch all 4 series concurrently.
8. **Regime classification**: Simple rule-based classifier from GDP growth, inflation, unemployment. No LLM needed.
9. **Percentage change computation**: GDP and CPI are level values; the connector computes % change from the last 2 observations.

## Constraints

- All functions are `async def` (except `_classify_regime` which is pure computation).
- API key sourced from `config.settings.get_settings().FRED_API_KEY` -- never hardcoded.
- Cache TTL is 3600 seconds (1 hour). `maxsize=64`.
- `httpx.AsyncClient` timeout is 10 seconds.
- Return `{}` (empty dict) on any error -- never raise to caller.
- FRED API requires `file_type=json` query param.
- FRED API requires `api_key` as query parameter.
- `_fetch_series` fetches `limit=2` observations (need 2 for % change calculations).
- Values from FRED are strings -- must be parsed to float (handle "." which means missing).

## Test Requirements

All tests must mock `httpx.AsyncClient` -- no real network calls.

1. **Macro indicators success**: Mock all 4 series responses, assert returned dict has all 5 keys with correct values.
2. **GDP growth calculation**: Mock 2 GDP observations, assert correct YoY % change.
3. **Inflation rate calculation**: Mock 2 CPI observations, assert correct % change.
4. **Fed funds rate**: Mock response, assert value extracted directly.
5. **Unemployment rate**: Mock response, assert value extracted directly.
6. **Macro indicators partial failure**: Mock 1 series failing, assert other indicators still returned, failed one is None.
7. **Macro indicators total failure**: Mock all series failing, assert `{}`.
8. **FRED missing value "."**: Mock observation with value ".", assert indicator is None.
9. **Regime expansion**: gdp > 2.0, inflation < 4.0 -> "expansion".
10. **Regime contraction**: gdp < 0.0 -> "contraction".
11. **Regime stagflation**: gdp < 2.0, inflation > 4.0 -> "stagflation".
12. **Regime recovery**: 0.0 < gdp <= 2.0, inflation <= 4.0 -> "recovery".
13. **Regime None**: insufficient data -> None.
14. **Cache hit**: Call `get_macro_indicators` twice, assert HTTP called only once per series.
15. **Settings injection**: Confirm API key from settings used in requests.
16. **Module singleton**: `from tools.fred_connector import fred` works.
17. **Close method**: `await fred.close()` calls `client.aclose()`.

## Acceptance Criteria

- [ ] `tools/fred_connector.py` exists with `FredConnector` class
- [ ] `tools/__init__.py` exists (package init)
- [ ] `get_macro_indicators()` async method returns all 4 indicators + macro_regime
- [ ] `_fetch_series()` async method fetches individual FRED series
- [ ] `_classify_regime()` method classifies macro regime from indicators
- [ ] `close()` async method for client cleanup
- [ ] TTLCache with maxsize=64, ttl=3600
- [ ] httpx.AsyncClient with timeout=10.0
- [ ] API key from Settings (dependency injection)
- [ ] All external calls wrapped in try/except
- [ ] Returns {} on any error
- [ ] Handles FRED "." missing values gracefully
- [ ] Parallel fetching with asyncio.gather
- [ ] Module-level `fred` singleton
- [ ] All tests pass (`pytest tests/test_fred_connector.py -v`)
- [ ] Ruff clean (`ruff check tools/fred_connector.py`)
