"""NewsAPI async wrapper with sentiment scoring and TTL caching.

Provides news sentiment data for the PulseMonitor agent.
"""

from __future__ import annotations

import httpx
from cachetools import TTLCache

from config.settings import Settings, get_settings


class NewsConnector:
    """Async NewsAPI wrapper with keyword-based sentiment scoring and TTL caching."""

    EVENT_KEYWORDS: dict[str, list[str]] = {
        "earnings": ["earnings", "quarterly results", "revenue beat", "revenue miss", "eps"],
        "merger": ["merger", "acquisition", "buyout", "takeover"],
        "lawsuit": ["lawsuit", "litigation", "sued", "legal action", "settlement"],
        "fda": ["fda", "drug approval", "clinical trial", "phase 3"],
        "management": ["ceo", "cfo", "resigned", "appointed", "executive"],
        "dividend": ["dividend", "buyback", "share repurchase"],
    }

    POSITIVE_KEYWORDS: list[str] = [
        "surge",
        "soar",
        "jump",
        "gain",
        "rally",
        "beat",
        "upgrade",
        "bullish",
        "growth",
        "profit",
        "record high",
        "outperform",
        "strong",
        "positive",
        "optimistic",
        "exceed",
    ]

    NEGATIVE_KEYWORDS: list[str] = [
        "plunge",
        "crash",
        "drop",
        "fall",
        "decline",
        "miss",
        "downgrade",
        "bearish",
        "loss",
        "warning",
        "concern",
        "weak",
        "negative",
        "pessimistic",
        "underperform",
        "cut",
        "layoff",
        "recall",
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        s = settings or get_settings()
        self.api_key = s.NEWS_API_KEY
        self.base_url = "https://newsapi.org"
        self.cache: TTLCache = TTLCache(maxsize=64, ttl=300)
        self.client = httpx.AsyncClient(timeout=10.0)

    async def _fetch_articles(self, query: str, page_size: int = 20) -> list[dict]:
        """Fetch articles from NewsAPI /v2/everything. Returns [] on error."""
        cache_key = f"news_{query}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            url = f"{self.base_url}/v2/everything"
            params = {
                "q": query,
                "apiKey": self.api_key,
                "pageSize": page_size,
                "sortBy": "publishedAt",
                "language": "en",
            }

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return []

            data = response.json()
            articles = data.get("articles", [])

            self.cache[cache_key] = articles
            return articles
        except Exception:
            return []

    async def get_news_sentiment(self, ticker: str) -> dict:
        """Fetch news for a ticker and compute sentiment. Returns {} on total failure."""
        cache_key = f"sentiment_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            articles = await self._fetch_articles(ticker)

            if not articles:
                result = {
                    "sentiment_score": 0.0,
                    "article_count": 0,
                    "top_headlines": [],
                    "event_flags": [],
                }
                self.cache[cache_key] = result
                return result

            scores = []
            for article in articles:
                title = article.get("title", "") or ""
                description = article.get("description", "") or ""
                text = f"{title} {description}"
                scores.append(self._score_text(text))

            avg_score = sum(scores) / len(scores) if scores else 0.0
            avg_score = max(-1.0, min(1.0, avg_score))

            top_headlines = [article.get("title", "") for article in articles[:5]]
            event_flags = self._detect_events(articles)

            result = {
                "sentiment_score": avg_score,
                "article_count": len(articles),
                "top_headlines": top_headlines,
                "event_flags": event_flags,
            }

            self.cache[cache_key] = result
            return result
        except Exception:
            return {}

    def _score_text(self, text: str | None) -> float:
        """Score a single text string for sentiment. Returns 0.0 for empty/None."""
        if not text:
            return 0.0

        text_lower = text.lower()
        pos_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text_lower)
        neg_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        score = (pos_count - neg_count) / total
        return max(-1.0, min(1.0, score))

    def _detect_events(self, articles: list[dict]) -> list[str]:
        """Scan articles for event keywords. Returns unique event category names."""
        detected = set()

        for article in articles:
            title = (article.get("title", "") or "").lower()
            description = (article.get("description", "") or "").lower()
            combined = f"{title} {description}"

            for category, keywords in self.EVENT_KEYWORDS.items():
                if any(kw in combined for kw in keywords):
                    detected.add(category)

        return sorted(detected)

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()


news = NewsConnector()
