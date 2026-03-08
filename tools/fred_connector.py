"""FRED API async wrapper with TTL caching.

Provides macroeconomic indicators for the EconomyWatcher agent.
"""

from __future__ import annotations

import asyncio

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings


class FredConnector:
    """Async FRED API wrapper with 1-hour TTL cache."""

    SERIES_MAP: dict[str, str] = {
        "gdp_growth": "GDP",
        "inflation_rate": "CPIAUCSL",
        "fed_funds_rate": "FEDFUNDS",
        "unemployment_rate": "UNRATE",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.api_key = s.FRED_API_KEY
        self.base_url = "https://api.stlouisfed.org"
        self.cache: TTLCache = TTLCache(maxsize=64, ttl=3600)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def _fetch_series(self, series_id: str, limit: int = 2) -> list[dict]:
        """Fetch latest observations for a FRED series. Returns [] on error."""
        cache_key = f"fred_{series_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/fred/series/observations"
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "sort_order": "desc",
                "limit": limit,
            }

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return []

            data = response.json()
            observations = data.get("observations", [])

            self.cache[cache_key] = observations
            return observations
        except Exception:
            return []

    async def get_macro_indicators(self) -> dict:
        """Fetch all 4 macro indicators in parallel. Returns {} on total failure."""
        cache_key = "macro_indicators"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            gdp_obs, cpi_obs, fedfunds_obs, unrate_obs = await asyncio.gather(
                self._fetch_series(self.SERIES_MAP["gdp_growth"]),
                self._fetch_series(self.SERIES_MAP["inflation_rate"]),
                self._fetch_series(self.SERIES_MAP["fed_funds_rate"]),
                self._fetch_series(self.SERIES_MAP["unemployment_rate"]),
            )

            gdp_growth = self._pct_change(gdp_obs)
            inflation_rate = self._pct_change(cpi_obs)
            fed_funds_rate = self._parse_latest(fedfunds_obs)
            unemployment_rate = self._parse_latest(unrate_obs)

            # If all indicators are None, return {}
            if all(
                v is None
                for v in [gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate]
            ):
                return {}

            macro_regime = self._classify_regime(
                gdp_growth, inflation_rate, unemployment_rate
            )

            result = {
                "gdp_growth": gdp_growth,
                "inflation_rate": inflation_rate,
                "fed_funds_rate": fed_funds_rate,
                "unemployment_rate": unemployment_rate,
                "macro_regime": macro_regime,
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    def _parse_value(self, value_str: str) -> float | None:
        """Parse a FRED observation value. Returns None for '.' (missing)."""
        if value_str == ".":
            return None
        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None

    def _parse_latest(self, observations: list[dict]) -> float | None:
        """Extract the latest value from observations."""
        if not observations:
            return None
        return self._parse_value(observations[0].get("value", "."))

    def _pct_change(self, observations: list[dict]) -> float | None:
        """Compute % change from the last 2 observations."""
        if len(observations) < 2:
            return None

        current = self._parse_value(observations[0].get("value", "."))
        previous = self._parse_value(observations[1].get("value", "."))

        if current is None or previous is None or previous == 0:
            return None

        return (current - previous) / previous * 100

    def _classify_regime(
        self,
        gdp_growth: float | None,
        inflation_rate: float | None,
        unemployment_rate: float | None,
    ) -> str | None:
        """Classify macro regime from indicators."""
        if gdp_growth is None:
            return None

        if gdp_growth < 0.0:
            return "contraction"
        if inflation_rate is not None and inflation_rate > 4.0 and gdp_growth < 2.0:
            return "stagflation"
        if inflation_rate is not None and inflation_rate < 4.0 and gdp_growth > 2.0:
            return "expansion"
        if gdp_growth > 0.0 and gdp_growth <= 2.0:
            if inflation_rate is None or inflation_rate <= 4.0:
                return "recovery"

        return None

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


fred = FredConnector()
