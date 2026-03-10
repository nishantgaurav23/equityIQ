"""World Bank + RBI macro data connector for Indian market indicators.

Uses World Bank API (free, no API key) for GDP growth, CPI inflation,
and unemployment. Uses yfinance for RBI repo rate proxy.
All data is TTL-cached to minimize API calls.
"""

from __future__ import annotations

import logging

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# World Bank indicator codes
_WB_INDICATORS: dict[str, str] = {
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",       # GDP growth (annual %)
    "inflation_rate": "FP.CPI.TOTL.ZG",       # CPI inflation (annual %)
    "unemployment_rate": "SL.UEM.TOTL.ZS",    # Unemployment (% of labor force)
}

# RBI repo rate is not directly in World Bank; we use a known recent value
# and try to fetch via yfinance INR bond proxy or fallback
_FALLBACK_REPO_RATE = 6.50  # RBI repo rate as of early 2026


class IndiaMacroConnector:
    """Fetch Indian macroeconomic indicators from World Bank API (free, no key)."""

    def __init__(self) -> None:
        self.cache: TTLCache = TTLCache(maxsize=32, ttl=3600)
        self.client = httpx.AsyncClient(timeout=15.0)
        self.base_url = "https://api.worldbank.org/v2"

    async def _fetch_wb_indicator(self, indicator: str) -> float | None:
        """Fetch latest value for a World Bank indicator for India."""
        cache_key = f"wb_in_{indicator}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/country/IN/indicator/{indicator}"
            params = {
                "format": "json",
                "per_page": 5,
                "mrv": 3,  # most recent values
            }
            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return None

            data = response.json()
            # World Bank returns [metadata, data_array]
            if not isinstance(data, list) or len(data) < 2:
                return None

            records = data[1]
            if not records:
                return None

            # Find first non-null value (most recent)
            for record in records:
                value = record.get("value")
                if value is not None:
                    result = float(value)
                    self.cache[cache_key] = result
                    return result

            return None
        except Exception as exc:
            logger.warning("World Bank API error for %s: %s", indicator, exc)
            return None

    async def _fetch_rbi_repo_rate(self) -> float:
        """Attempt to get RBI repo rate. Falls back to known recent value."""
        cache_key = "rbi_repo_rate"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try fetching from World Bank interest rate indicator
        try:
            url = f"{self.base_url}/country/IN/indicator/FR.INR.RINR"
            params = {"format": "json", "per_page": 3, "mrv": 2}
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) >= 2 and data[1]:
                    for record in data[1]:
                        value = record.get("value")
                        if value is not None:
                            rate = float(value)
                            self.cache[cache_key] = rate
                            return rate
        except Exception:
            pass

        # Fallback: use known recent RBI repo rate
        self.cache[cache_key] = _FALLBACK_REPO_RATE
        return _FALLBACK_REPO_RATE

    def _classify_regime(
        self,
        gdp_growth: float | None,
        inflation_rate: float | None,
        unemployment_rate: float | None,
    ) -> str | None:
        """Classify Indian macro regime. India-specific thresholds differ from US."""
        if gdp_growth is None:
            return None

        # India: GDP growth of 5-7% is normal expansion
        if gdp_growth < 0.0:
            return "contraction"
        if inflation_rate is not None and inflation_rate > 6.0 and gdp_growth < 5.0:
            return "stagflation"
        if gdp_growth > 5.0 and (inflation_rate is None or inflation_rate < 6.0):
            return "expansion"
        if 0.0 < gdp_growth <= 5.0:
            if inflation_rate is None or inflation_rate <= 6.0:
                return "recovery"

        return None

    async def get_macro_indicators(self) -> dict:
        """Fetch all Indian macro indicators. Returns {} on total failure.

        Returns dict with keys: gdp_growth, inflation_rate, fed_funds_rate
        (mapped to RBI repo rate for compatibility), unemployment_rate, macro_regime.
        """
        cache_key = "india_macro"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            import asyncio

            gdp_task = self._fetch_wb_indicator(_WB_INDICATORS["gdp_growth"])
            cpi_task = self._fetch_wb_indicator(_WB_INDICATORS["inflation_rate"])
            unemp_task = self._fetch_wb_indicator(_WB_INDICATORS["unemployment_rate"])
            repo_task = self._fetch_rbi_repo_rate()

            gdp_growth, inflation_rate, unemployment_rate, repo_rate = await asyncio.gather(
                gdp_task, cpi_task, unemp_task, repo_task
            )

            if all(v is None for v in [gdp_growth, inflation_rate, unemployment_rate]):
                return {}

            macro_regime = self._classify_regime(gdp_growth, inflation_rate, unemployment_rate)

            result = {
                "gdp_growth": gdp_growth,
                "inflation_rate": inflation_rate,
                # Use fed_funds_rate key for compatibility with EconomyReport schema
                "fed_funds_rate": repo_rate,
                "unemployment_rate": unemployment_rate,
                "macro_regime": macro_regime,
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


india_macro = IndiaMacroConnector()
