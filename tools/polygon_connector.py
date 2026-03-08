"""Polygon.io async API wrapper with TTL caching.

Provides market data for ValuationScout, MomentumTracker, PulseMonitor, and RiskGuardian.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings


class PolygonConnector:
    """Async Polygon.io API wrapper with 5-minute TTL cache."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.api_key = s.POLYGON_API_KEY
        self.base_url = "https://api.polygon.io"
        self.cache: TTLCache = TTLCache(maxsize=128, ttl=300)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_fundamentals(self, ticker: str) -> dict:
        """Fetch latest financial ratios for a ticker. Returns {} on error."""
        cache_key = f"fundamentals_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/vX/reference/financials"
            params = {"ticker": ticker, "limit": 1, "apiKey": self.api_key}

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return {}

            data = response.json()
            results = data.get("results", [])
            if not results:
                return {}

            filing = results[0]
            financials = filing.get("financials", {})
            income = financials.get("income_statement", {})
            balance = financials.get("balance_sheet", {})
            cash_flow = financials.get("cash_flow_statement", {})

            result = {
                "pe_ratio": filing.get("pe_ratio"),
                "pb_ratio": filing.get("pb_ratio"),
                "revenue_growth": income.get("revenues", {}).get("value"),
                "debt_to_equity": balance.get("debt_to_equity_ratio", {}).get("value"),
                "fcf_yield": cash_flow.get("free_cash_flow", {}).get("value"),
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def get_price_history(self, ticker: str, days: int = 90) -> dict:
        """Fetch daily OHLCV bars for the last N days. Returns {} on error."""
        cache_key = f"price_{ticker}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            url = (
                f"{self.base_url}/v2/aggs/ticker/{ticker}"
                f"/range/1/day/{from_date}/{to_date}"
            )
            params = {"adjusted": "true", "sort": "asc", "apiKey": self.api_key}

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return {}

            data = response.json()
            bars = data.get("results")
            if not bars:
                return {}

            prices = []
            volumes = []
            dates = []

            for bar in bars:
                prices.append(bar.get("c", 0.0))
                volumes.append(bar.get("v", 0.0))
                dates.append(
                    datetime.fromtimestamp(bar["t"] / 1000).strftime("%Y-%m-%d")
                )

            result = {"prices": prices, "volumes": volumes, "dates": dates}
            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def get_company_news(self, ticker: str, limit: int = 10) -> dict:
        """Fetch recent news articles for a ticker. Returns {} on error."""
        cache_key = f"news_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/v2/reference/news"
            params = {"ticker": ticker, "limit": limit, "apiKey": self.api_key}

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return {}

            data = response.json()
            items = data.get("results")
            if not items:
                return {}

            headlines = []
            articles = []

            for item in items:
                headlines.append(item.get("title", ""))
                articles.append({
                    "title": item.get("title", ""),
                    "published_utc": item.get("published_utc", ""),
                })

            result = {"headlines": headlines, "articles": articles}
            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


polygon = PolygonConnector()
