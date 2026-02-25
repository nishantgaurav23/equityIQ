"""
What it does:

    Fetches news headlines from NewsAPI and scores sentiments. Unlike polygon_connector.py whihc just fetches raw
    data, this also computest a sentiment score from the headlines before returning - so PulseMonitor gets
    pre-processed data.

Why It's Needed:

    PulseMonitor needs two things: headines and a sentiment score. NewsAPI provides headlines but no sentiment - this
    file bridges that gap using keyword matching.

How It Helps:
    - agetns/pulse_montior.py calls get_news_sentiment(ticker) - gets everything it needs in one call
    - No external ML library needed - simple keyword scoring is fast and reliable enough

---

What to notice

    Pattern: score_sentiment and detect_events are def not async def
    Why: No API call — pure Python, no need for await
    ────────────────────────────────────────
    Pattern: detected = set() in detect_events
    Why: Prevents duplicate flags e.g. two headlines both say "lawsuit"
    ────────────────────────────────────────
    Pattern: headlines[:3]
    Why: Slices first 3 only for top_headlines field in PulseReport
    ────────────────────────────────────────
    Pattern: get_headlines caches, get_news_sentiment does not
    Why: Avoids double-caching the same data
"""
import os
import httpx
from cachetools import TTLCache
from dotenv import load_dotenv

load_dotenv()

class NewsConnector:
    """Async NewsAPI wrapper with TTL caching and built-in sentiment scoring."""

    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY", "")
        self.base_url = "https://newsapi.org/v2"
        self.cache = TTLCache(maxsize=64, ttl=600)
        self.client = httpx.AsyncClient(timeout=10.0)
        self.positive_keywords = [
            "beat", "record", "launch", "upgrade", "partnership",
            "growth", "profit", "exceeded", "surpassed", "bullish",
            "breakthrough", "expansion", "strong", "raised", "dividend"
            
            ]
        self.negative_keywords = [
            "miss", "recall", "lawsuit", "investigation", "decline",
            "downgrade", "loss", "fell short", "below", "bearish",
            "fraud", "probe", "layoffs", "cut", "warning"
            ]

    async def get_headlines(self, ticker: str, limit: int = 10) -> list[dict]:
        """
        Fetches raw headlines for a ticker from NewsAPI.
        Private helper — called by get_news_sentiment only.
        Returns list of dicts with title and publishedAt.
        Returns empty list on failure.
        Args:
            ticker: str <- e.g. "AAPL"
            limit: int <- default 10

        Returns:
            list[dict] <- each dict has "title" and "publishedAT"
            [] <- empty list on failure
        """
        cache_key = f"headlines_{ticker}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                "q":        ticker,
                "pageSize": limit,
                "sortBy":   "publishedAt",
                "language": "en",
                "apiKey":   self.api_key,
            }

            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                return []
            
            data = response.json()
            if "articles" not in data:
                return []
            
            articles = data["articles"]
            if len(articles) == 0:
                return []
            
            result = [
                {
                    "title": article.get("title", ""),
                    "publishedAt": article.get("publishedAt", "")
                }
                for article in articles
                
            ]

            self.cache[cache_key] = result
            return result
        
        except Exception:
            return []
        
    def score_sentiment(self, headlines: list[str]) -> float:
        """
        Score sentiment from a list of headline strings using keyword matching.
        No API call - pure Python logic
        Returns float between -1.0 and +1.0 if headlines empty

        How to calculate:
            For each headline:
            count how many positive_keywords appear → positive_hits
            count how many negative_keywords appear → negative_hits

            total_score = (positive_hits - negative_hits) / total_headlines
            clamp result to [-1.0, 1.0]

        Args:
            headlines: list[str]

        Returns:
            float  ← between -1.0 and +1.0
            0.0    ← if headlines list is empty
        """
        if len(headlines) == 0:
            return 0.0

        try:
            positive_hits = 0
            negative_hits = 0

            for headline in headlines:
                headline_lower = headline.lower()
                for word in self.positive_keywords:
                    if word in headline_lower:
                        positive_hits += 1
                for word in self.negative_keywords:
                    if word in headline_lower:
                        negative_hits += 1

            total = len(headlines)
            raw_score = (positive_hits - negative_hits) / total
            return max(-1.0, min(1.0, raw_score))
        
        except Exception:
            return 0.0
        
    def detect_events(self, headlines: list[str]) -> list[str]:
        """
        Scan headlines for high-impact financial events.
        Returns list of even flag strings matching PulseReport.event_flags.
        Returns empty list if no events detected or headlines empty

        Args:
            headlines: list[str]

        Returns:
            list[str]  ← e.g. ["earnings_beat", "downgrade"]
            []         ← if no events detected
        """
        if len(headlines) == 0:
            return []
        
        try:
            event_rules = {
                "earnings_beat":  ["beat", "exceeded", "surpassed"],
                "earnings_miss":  ["miss", "fell short", "below expectations"],
                "lawsuit":        ["lawsuit", "sued", "litigation"],
                "product_launch": ["launch", "unveiled", "released"],
                "investigation":  ["investigation", "probe", "sec inquiry"],
                "upgrade":        ["upgrade", "raised target"],
                "downgrade":      ["downgrade", "lowered target"],
                "insider_trade":  ["insider", "form 4", "executive sold"],
            }

            detected = set()

            for headline in headlines:
                headline_lower = headline.lower()
                for flag, keywords in event_rules.items():
                    for keyword in keywords:
                        if keyword in headline_lower:
                            detected.add(flag)
            
            return list(detected)
        
        except Exception:
            return []
        
    async def get_news_sentiment(self, ticker: str, limit: int = 10) -> dict:
        """
        Main function called by PulseMonitor.
        Comines get_headlines + score_sentiment + detect_events in one call.
        Returns dict with sentiment_score, article_count, top_headlines, event_flags.
        Return empty dict on failure

        Args:
            ticker: str
            limit:  int  ← default 10

        Returns:
            dict with keys:
            sentiment_score: float       ← from score_sentiment()
            article_count:   int         ← len of headlines
            top_headlines:   list[str]   ← first 3 headline strings only
            event_flags:     list[str]   ← from detect_events()
            {} ← empty dict on failure
        """
        try:
            articles = await self.get_headlines(ticker, limit)
            headlines = [a["title"] for a in articles]

            sentiment = self.score_sentiment(headlines)
            events = self.detect_events(headlines)
            top_3 = headlines[:3]

            return {
                "sentiment_score": sentiment,
                "article_count": len(headlines),
                "top_headlines": top_3,
                "event_flags": events,
            }
        
        except Exception:
            return {}
        
news = NewsConnector()


    
