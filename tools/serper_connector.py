"""Serper.dev (Google Search API) connector with TTL caching.

Provides structured Google search results for financial intelligence:
- Web search: analyst reports, company news, sector trends
- News search: real-time financial news from Google News
- Used by agents (PulseMonitor, ComplianceChecker, EconomyWatcher) and chat engine.
"""

from __future__ import annotations

import logging

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class SerperConnector:
    """Async Serper.dev API wrapper with 5-minute TTL cache."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.api_key = s.SERPER_API_KEY
        self.base_url = "https://google.serper.dev"
        self.cache: TTLCache = TTLCache(maxsize=128, ttl=300)
        self.client = httpx.AsyncClient(timeout=15.0)

    @property
    def available(self) -> bool:
        """Check if Serper API key is configured."""
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
    ) -> dict:
        """Run a Google search via Serper.

        Args:
            query: Search query string.
            num_results: Number of results (max 100).
            search_type: "search" (web) or "news".

        Returns:
            Dict with "results" list of {title, snippet, link} dicts,
            plus "knowledge_graph" if available. Empty dict on error.
        """
        if not self.api_key:
            return {}

        cache_key = f"serper_{search_type}_{query}_{num_results}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/{search_type}"
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {"q": query, "num": num_results}

            response = await self.client.post(
                url, json=payload, headers=headers
            )
            if response.status_code != 200:
                logger.warning(
                    "Serper %s returned %d for query: %s",
                    search_type, response.status_code, query,
                )
                return {}

            data = response.json()

            # Normalize response format
            results: list[dict] = []

            # Web search results
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", ""),
                })

            # News search results
            for item in data.get("news", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", ""),
                    "source": item.get("source", ""),
                })

            output = {"results": results}

            # Include knowledge graph if present (company info, stock price)
            kg = data.get("knowledgeGraph")
            if kg:
                output["knowledge_graph"] = {
                    "title": kg.get("title", ""),
                    "description": kg.get("description", ""),
                    "type": kg.get("type", ""),
                    "attributes": kg.get("attributes", {}),
                }

            # Include answer box if present
            ab = data.get("answerBox")
            if ab:
                output["answer_box"] = {
                    "title": ab.get("title", ""),
                    "answer": ab.get("answer", ""),
                    "snippet": ab.get("snippet", ""),
                }

            self.cache[cache_key] = output
            return output

        except Exception as exc:
            logger.warning("Serper search failed for '%s': %s", query, exc)
            return {}

    async def search_stock_news(self, ticker: str, company_name: str = "") -> dict:
        """Search for latest stock news and analyst opinions.

        Combines ticker and company name for best coverage.
        Returns dict with "results" list and optional "knowledge_graph".
        """
        query = f"{ticker} stock"
        if company_name:
            query = f"{company_name} ({ticker}) stock news"
        return await self.search(query, num_results=10, search_type="news")

    async def search_analyst_reports(self, ticker: str) -> dict:
        """Search for analyst reports and price targets for a stock."""
        query = f"{ticker} stock analyst report price target 2026"
        return await self.search(query, num_results=8)

    async def search_sector_trends(self, sector: str) -> dict:
        """Search for sector/industry trend analysis."""
        query = f"{sector} sector outlook trends 2026"
        return await self.search(query, num_results=8)

    async def search_regulatory_news(
        self, ticker: str, company_name: str = ""
    ) -> dict:
        """Search for regulatory news, investigations, compliance issues."""
        name = company_name or ticker
        query = f"{name} regulatory investigation compliance SEC SEBI 2026"
        return await self.search(query, num_results=8, search_type="news")

    async def search_macro_outlook(self, market: str = "US") -> dict:
        """Search for macroeconomic outlook and policy news."""
        if market.upper() == "INDIA":
            query = "India economy outlook RBI interest rate GDP 2026"
        else:
            query = "US economy outlook Federal Reserve interest rate GDP 2026"
        return await self.search(query, num_results=8, search_type="news")

    async def search_general_finance(self, query: str) -> dict:
        """Search for general financial topics and concepts."""
        return await self.search(query, num_results=8)

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


serper = SerperConnector()
