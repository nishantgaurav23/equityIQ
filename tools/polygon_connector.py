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
            # Fetch 2 periods to compute YoY revenue growth
            url = f"{self.base_url}/vX/reference/financials"
            params = {"ticker": ticker, "limit": 2, "apiKey": self.api_key}

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

            # Revenue growth: YoY decimal fraction (0.25 = 25%)
            revenue_growth = None
            current_revenue = income.get("revenues", {}).get("value")
            if len(results) >= 2 and current_revenue:
                prev_financials = results[1].get("financials", {})
                prev_income = prev_financials.get("income_statement", {})
                prev_revenue = prev_income.get("revenues", {}).get("value")
                if prev_revenue and prev_revenue != 0:
                    revenue_growth = round(
                        (current_revenue - prev_revenue) / abs(prev_revenue), 4
                    )

            # Compute PE ratio: need EPS from income statement
            pe_ratio = None
            eps_value = income.get("basic_earnings_per_share", {}).get("value")
            if eps_value and eps_value != 0:
                # Get current price from snapshot
                price = await self._get_current_price(ticker)
                if price:
                    pe_ratio = round(price / eps_value, 2)

            # Compute PB ratio: price / book value per share
            pb_ratio = None
            equity = balance.get("equity", {}).get("value")
            shares = income.get(
                "basic_average_shares", {}
            ).get("value") or balance.get(
                "common_stock_shares_outstanding", {}
            ).get("value")
            if equity and shares and shares != 0:
                book_per_share = equity / shares
                if book_per_share != 0:
                    price = await self._get_current_price(ticker)
                    if price:
                        pb_ratio = round(price / book_per_share, 2)

            # Debt-to-equity: total liabilities / equity (or use direct field)
            debt_to_equity = balance.get("debt_to_equity_ratio", {}).get("value")
            if debt_to_equity is None:
                total_liabilities = balance.get("liabilities", {}).get("value")
                equity_val = balance.get("equity", {}).get("value")
                if total_liabilities and equity_val and equity_val != 0:
                    debt_to_equity = round(total_liabilities / equity_val, 2)

            # FCF yield: free cash flow / market cap as decimal fraction (0.05 = 5%)
            fcf_yield = None
            fcf = cash_flow.get("net_cash_flow_from_operating_activities", {}).get("value")
            capex = cash_flow.get(
                "net_cash_flow_from_investing_activities_continuing", {}
            ).get("value")
            if fcf is None:
                fcf = cash_flow.get("free_cash_flow", {}).get("value")
            elif capex is not None:
                fcf = fcf + capex  # capex is typically negative
            if fcf and shares:
                price = await self._get_current_price(ticker)
                if price and price != 0:
                    market_cap = price * shares
                    if market_cap != 0:
                        fcf_yield = round(fcf / market_cap, 4)

            result = {
                "pe_ratio": pe_ratio,
                "pb_ratio": pb_ratio,
                "revenue_growth": revenue_growth,
                "debt_to_equity": debt_to_equity,
                "fcf_yield": fcf_yield,
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def _get_current_price(self, ticker: str) -> float | None:
        """Fetch current stock price from Polygon snapshot. Returns None on error."""
        cache_key = f"price_snapshot_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/v2/aggs/ticker/{ticker}/prev"
            params = {"adjusted": "true", "apiKey": self.api_key}
            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return None
            data = response.json()
            bars = data.get("results", [])
            if not bars:
                return None
            price = bars[0].get("c")
            if price:
                self.cache[cache_key] = price
            return price
        except Exception:
            return None

    async def get_price_history(self, ticker: str, days: int = 90) -> dict:
        """Fetch daily OHLCV bars for the last N days. Returns {} on error."""
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
            bars = data.get("results")
            if not bars:
                return {}

            prices = []
            volumes = []
            dates = []

            for bar in bars:
                prices.append(bar.get("c", 0.0))
                volumes.append(bar.get("v", 0.0))
                dates.append(datetime.fromtimestamp(bar["t"] / 1000).strftime("%Y-%m-%d"))

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
                articles.append(
                    {
                        "title": item.get("title", ""),
                        "published_utc": item.get("published_utc", ""),
                    }
                )

            result = {"headlines": headlines, "articles": articles}
            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


polygon = PolygonConnector()
