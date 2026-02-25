"""
What it does:
    This is the data fetcher to Polygon.io - the primary data source for EuityIQ. It makes HHPT calls to the Polygon.io
    REST API and returns structured data that the agents will use to make decisions.

    Three agents depends on this fule directly:
    - ValuationScout - needs fundamentals (P/E, P/B, revenue, debt)
    - MomentumTracker - needs historical price data and volumne
    - PulseMonitor - needs company-speciifc news

Why it's needed:
    Without this, agents have no real data. This file is also where TTL caching lives - so if two agents request the
    same ticker wihtin 5 minutes, the second call is served from. cache instead of buring an API rate limit.

How it Helps the Rest of the project

    - agents/valuation_scout.py calls get_fundamentals(ticker)
    - agents/momentum_tracker.py calls get_price_history(ticker, days)
    - agents/pulse_monitor.py calls get_company_news(ticker)
    - models/risk_calculator.py calls get_price_history(ticker, days=365)

---
Concepts to Know Before Writing

  - httpx — async HTTP client (replaces requests for async code)
  - cachetools.TTLCache — cache with automatic expiry
  - asyncio — async def + await for non-blocking API calls
  - os.getenv() — reads POLYGON_API_KEY from .env
  - try/except — never let a failed API call crash an agent

---
Class and Functions to Define 
tools/
  └── polygon_connector.py
      ├── class PolygonConnector
      │   ├── __init__(self)
      │   ├── get_fundamentals(ticker) -> dict
      │   ├── get_price_history(ticker, days) -> dict
      │   └── get_company_news(ticker, limit) -> dict
      └── polygon  ← singleton instance at bottom of file
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import httpx
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

class PolygonConnector:
    """Asyncio Polygon.io API wrapper with TTL caching."""

    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY", "")
        self.base_url = "https://api.polygon.io"
        self.cache = TTLCache(maxsize=128, ttl=300)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def get_fundamentals(self, ticker: str) -> dict:
        """Fetch financial ratios and fundamentals from Polygon.io."""
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
            
            financials = results[0].get("financials", {})
            income = financials.get("income_statement", {})
            balance = financials.get("balance_sheet", {})
            cash_flow = financials.get("cash_flow_statement", {})

            result = {
                "pe_ratio": results[0].get("pe_ratio"),
                "pb_ratio": results[0].get("pb_ratio"),
                "revenue_growth": income.get("revenues", {}).get("value"),
                "debt_to_equity": balance.get("debt_to_equity_ratio", {}).get("value"),
                "fcf_yield": cash_flow.get("free_cash_flow", {}).get("value")
            }

            self.cache[cache_key] = result
            return result
        
        except Exception:
            return {}
        
    async def get_price_history(self, ticker: str, days: int = 90) -> dict:
        """
        Fetch daily OHLCV price history from a ticker from Polygon.io
        Used by MomentumTracker for RSI/MACD calculations and 
        RiskGuardian for volatility and drawdown calculations.
        Returns dict with prices, volumes, dates as list sorted oldest to newest.
        Returns empty dict if ticker is invalid or API call fails.
        """
        cache_key = f"price_{ticker}_{days}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            to_date = datetime.now().strftime("%Y-%m-%d")
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/range/1/day/{from_date}/{to_date}"
            params = {"adjusted": "true", "sort": "asc", "apiKey": self.api_key}

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return {}
            
            data = response.json()
            if "results" not in data or len(data["results"]) == 0:
                return {}
            
            prices = []
            volumes = []
            dates = []

            for bar in data["results"]:
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
        """
        Fetch recent news articles for a ticker from Polygon.io.
        Used by PulseMonitor for sentiment scoring and event detection.
        Returns dict with headlines (list of strings) and articles (list of dicts).
        Each article dict contains title and published_utc.
        Returns empty dict if ticker is invalid or API call fails.
        """

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
            if "results" not in data or len(data["results"]) == 0:
                return {}
            
            headlines = []
            articles = []

            for item in data["results"]:
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


polygon = PolygonConnector()
