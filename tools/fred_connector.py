"""
What It Does:
    Fetches macroeconomic data from the FRED API (Federal Reserve Economic Data) maintained by the St. Louis Fed. 
    It retrieves GDP growth , inflation rate, Fed Funds Rate, and unemployment rate.

Why It's Needed:
    EconomyWatcher agent cannot reason about macro conditions without real data. FRED is the most reliable free
    source for US economic indicators - used by economists, analysts, and the FED itself.

How It Heps:
    - agents/economy_watcher,py calls this to populate EconomyReport
    - models/signal_fusion.py uses macro regime to adjust agent weights
    - No FRED data = Economy/Watcher returns empty report + low confidence
"""

import os
import httpx
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

class FredConnector:
    """Async FRED API wrapper with TTL caching."""

    def __init__(self):
        self.api_key = os.getenv("FRED_API_KEY", "")
        self.base_url = "https://api.stlouisfed.org/fred"
        self.cache = TTLCache(maxsize=64, ttl=3600)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_series_value(self, series_id: str) -> float | None:
        """
        Core private helper - fetches the latest value for any FRED series ID.
        All other functions call this one. Never called directly by agents.
        Returns the latest float value, or None if fetch fails.
        """
        cache_key = f"series_{series_id}"

        # Step 1: cache check
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            url = f"{self.base_url}/series/observations"
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "limit": 1,
                "sort_order": "desc"    # get most recent observation first
            }

            response = await self.client.get(url, params=params)

            # Step 2: status check
            if response.status_code != 200:
                return None
            
            data = response.json()

            # Step 3: key existence check
            if "observations" not in data:
                return None
            
            observations = data["observations"]

            # Step 4: empty list check
            if len(observations) == 0:
                return None
            
            # Step 5: extarct value - FRED returns strings, convert to float
            value = float(observations[0]["value"])

            # Step 6: store in cache and return
            self.cache[cache_key] = value
            return value
        
        except Exception:
            return None
        
    async def get_gdp_growth(self) -> float | None:
        """
        Latest US GDP growth rate (quarterly % annualized).
        EconomyWatcher uses this to classify expansion vs contraction.
        FRED series: GDP
        Returns: e.g. 2.8 means 2.8% growth. None if unavailable.
        """
        return await self.get_series_value("GDP")
    
    async def get_inflation_rate(self) -> float | None:
        """
        Current CPI inflation rate (Consumer Price Index, all urban consumers).
        Fed targets 2.0% — above 4.0% signals hawkish Fed, hurts growth stocks.
        FRED series: CPIAUCSL
        Returns: e.g. 3.2 means 3.2% inflation. None if unavailable.
        """
        return await self.get_series_value("CPIAUCSL")
    
    async def get_fed_funds_rate(self) -> float | None:
        """
        Current Federal Funds Rate set by the Federal Reserve.
        Rising = headwind for growth stocks. Falling = tailwind for equities.
        FRED series: FEDFUNDS
        Returns: e.g. 5.25 means 5.25% rate. None if unavailable.
        """
        return await self.get_series_value("FEDFUNDS")
    
    async def get_unemployment_rate(self) -> float | None:
        """
        Current US unemployment rate.
        Above 6.0% signals contraction. Below 4.5% signals healthy labor market.
        FRED series: UNRATE
        Returns: e.g. 4.1 means 4.1% unemployment. None if unavailable.
        
        """
        return await self.get_series_value("UNRATE")
    
    async def get_all_indicators(self) -> dict:
        """
        Fetches all 4 macro indicators in one call.
        This is what EconomyWatcher actually calls - not the individual functions.
        Returns dict with gdp_growth, inflation_rate, fed_fund_rate, unemployment_rate.
        Return empty dict {} on any failure.
        """
        try:
            gdp = await self.get_gdp_growth()
            inflation = await self.get_inflation_rate()
            fed_rate = await self.get_fed_funds_rate()
            unemployment = await self.get_unemployment_rate()

            return {
                "gdp_growth": gdp,
                "inflation_rate": inflation,
                "fed_funds_rate": fed_rate,
                "unemployment_rate": unemployment,
            }
        
        except Exception:
            return {}
        
fred = FredConnector()