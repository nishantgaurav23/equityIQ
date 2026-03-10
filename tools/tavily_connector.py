"""Tavily Search API connector with TTL caching.

Tavily is designed for AI agents — returns clean, summarized content
instead of raw HTML. Excellent for research-depth questions:
- Deep financial research and analysis
- Summarized answers with source citations
- Context-rich results for LLM consumption
"""

from __future__ import annotations

import logging

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class TavilyConnector:
    """Async Tavily Search API wrapper with 5-minute TTL cache."""

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.api_key = s.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
        self.cache: TTLCache = TTLCache(maxsize=128, ttl=300)
        self.client = httpx.AsyncClient(timeout=20.0)

    @property
    def available(self) -> bool:
        """Check if Tavily API key is configured."""
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 8,
        include_answer: bool = True,
        topic: str = "general",
    ) -> dict:
        """Run a Tavily search.

        Args:
            query: Search query.
            search_depth: "basic" (fast) or "advanced" (deeper, more tokens).
            max_results: Number of results (max 20).
            include_answer: Whether to include AI-generated answer summary.
            topic: "general" or "news" for news-focused results.

        Returns:
            Dict with "answer" (AI summary), "results" list of
            {title, content, url, score} dicts. Empty dict on error.
        """
        if not self.api_key:
            return {}

        cache_key = (
            f"tavily_{query}_{search_depth}_{max_results}_{topic}"
        )
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/search"
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": include_answer,
                "topic": topic,
            }

            response = await self.client.post(url, json=payload)
            if response.status_code != 200:
                logger.warning(
                    "Tavily returned %d for query: %s",
                    response.status_code, query,
                )
                return {}

            data = response.json()

            results: list[dict] = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "url": item.get("url", ""),
                    "score": item.get("score", 0),
                })

            output: dict = {"results": results}

            # Include AI-generated answer if available
            answer = data.get("answer")
            if answer:
                output["answer"] = answer

            self.cache[cache_key] = output
            return output

        except Exception as exc:
            logger.warning("Tavily search failed for '%s': %s", query, exc)
            return {}

    async def research_stock(
        self, ticker: str, company_name: str = ""
    ) -> dict:
        """Deep research on a stock — analyst opinions, outlook, risks."""
        name = company_name or ticker
        query = (
            f"{name} ({ticker}) stock analysis outlook risks "
            f"analyst opinion 2026"
        )
        return await self.search(
            query, search_depth="advanced", max_results=8
        )

    async def research_sector(self, sector: str) -> dict:
        """Research sector/industry trends and outlook."""
        query = f"{sector} industry sector outlook trends analysis 2026"
        return await self.search(
            query, search_depth="advanced", max_results=6
        )

    async def research_macro(self, market: str = "US") -> dict:
        """Research macroeconomic conditions and monetary policy."""
        if market.upper() == "INDIA":
            query = (
                "India economy 2026 RBI monetary policy GDP growth "
                "inflation outlook"
            )
        else:
            query = (
                "US economy 2026 Federal Reserve monetary policy GDP "
                "growth inflation outlook"
            )
        return await self.search(
            query, search_depth="advanced", max_results=6, topic="news"
        )

    async def research_topic(self, query: str) -> dict:
        """Research any financial/economic topic in depth."""
        return await self.search(
            query, search_depth="advanced", max_results=8,
            include_answer=True,
        )

    async def get_latest_news(
        self, ticker: str, company_name: str = ""
    ) -> dict:
        """Get latest news for a stock (news-focused search)."""
        name = company_name or ticker
        query = f"{name} ({ticker}) latest news"
        return await self.search(
            query, max_results=10, topic="news"
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


tavily = TavilyConnector()
