# S3.3 -- NewsAPI Async Connector + Sentiment Scoring

## Metadata

| Field | Value |
|-------|-------|
| Spec ID | S3.3 |
| Phase | 3 -- Data Connectors |
| Depends On | S1.3 (config/settings.py -- NEWS_API_KEY) |
| Location | `tools/news_connector.py` |
| Test File | `tests/test_news_connector.py` |
| Status | done |

## Purpose

Async wrapper around the NewsAPI REST API with built-in sentiment scoring. Provides news data consumed by the **PulseMonitor** agent (port 8003) to populate `PulseReport` fields: `sentiment_score`, `article_count`, `top_headlines`, and `event_flags`.

Sentiment scoring uses a keyword-based approach (no external NLP dependency) for speed and simplicity.

## API Endpoints Used

| Function | NewsAPI Endpoint | Notes |
|----------|-----------------|-------|
| `get_news_sentiment` | `GET /v2/everything` | Search by ticker/company name. Returns articles with title + description |

## Interface

```python
class NewsConnector:
    """Async NewsAPI wrapper with sentiment scoring and TTL caching."""

    # Event keywords that trigger event_flags
    EVENT_KEYWORDS: dict[str, list[str]] = {
        "earnings": ["earnings", "quarterly results", "revenue beat", "revenue miss", "EPS"],
        "merger": ["merger", "acquisition", "buyout", "takeover"],
        "lawsuit": ["lawsuit", "litigation", "sued", "legal action", "settlement"],
        "fda": ["FDA", "drug approval", "clinical trial", "phase 3"],
        "management": ["CEO", "CFO", "resigned", "appointed", "executive"],
        "dividend": ["dividend", "buyback", "share repurchase"],
    }

    # Sentiment keywords
    POSITIVE_KEYWORDS: list[str] = [
        "surge", "soar", "jump", "gain", "rally", "beat", "upgrade",
        "bullish", "growth", "profit", "record high", "outperform",
        "strong", "positive", "optimistic", "exceed",
    ]
    NEGATIVE_KEYWORDS: list[str] = [
        "plunge", "crash", "drop", "fall", "decline", "miss", "downgrade",
        "bearish", "loss", "warning", "concern", "weak", "negative",
        "pessimistic", "underperform", "cut", "layoff", "recall",
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        """
        Initialize with settings (dependency injection for testing).
        Falls back to get_settings() if not provided.
        - self.api_key: from settings.NEWS_API_KEY
        - self.base_url: "https://newsapi.org"
        - self.cache: TTLCache(maxsize=64, ttl=300)  # 5-minute TTL
        - self.client: httpx.AsyncClient(timeout=10.0)
        """

    async def _fetch_articles(self, query: str, page_size: int = 20) -> list[dict]:
        """
        Fetch articles from NewsAPI /v2/everything endpoint.
        URL: {base_url}/v2/everything?q={query}&apiKey={}&pageSize={}&sortBy=publishedAt&language=en
        Returns list of article dicts: [{"title": str, "description": str, "publishedAt": str}, ...]
        Returns [] on error.
        Cache key: f"news_{query}"
        """

    async def get_news_sentiment(self, ticker: str) -> dict:
        """
        Fetch news articles for a ticker and compute sentiment.
        Returns: {
            "sentiment_score": float,     # -1.0 to 1.0 (average across articles)
            "article_count": int,          # number of articles found
            "top_headlines": list[str],    # up to 5 headlines
            "event_flags": list[str],      # detected event categories
        }
        Returns {} on total failure.
        Cache key: f"sentiment_{ticker}"
        """

    def _score_text(self, text: str) -> float:
        """
        Score a single text string for sentiment.
        Count positive keyword matches, subtract negative keyword matches.
        Normalize to [-1.0, 1.0] range.
        Returns 0.0 for empty/None text.
        """

    def _detect_events(self, articles: list[dict]) -> list[str]:
        """
        Scan article titles and descriptions for event keywords.
        Returns list of unique event category names (e.g., ["earnings", "merger"]).
        """

    async def close(self) -> None:
        """Close the underlying httpx client."""

# Module-level singleton
news: NewsConnector
```

## Design Decisions

1. **Dependency injection**: `__init__` accepts optional `Settings` for testability. Falls back to `get_settings()`.
2. **TTLCache 5 minutes (300s)**: News changes frequently, but 5-min cache respects free-tier rate limits.
3. **`httpx.AsyncClient`**: Shared client with connection pooling. 10s timeout.
4. **Never crash**: Every external call wrapped in `try/except Exception`. Returns `{}` on failure.
5. **Module singleton**: `news = NewsConnector()` at module bottom for simple imports.
6. **`close()` method**: For graceful cleanup during app shutdown (lifespan hook).
7. **Keyword-based sentiment**: No external NLP library needed. Fast, deterministic, and testable. Positive/negative keyword counts normalized to [-1, 1].
8. **Event detection**: Scans titles+descriptions for event keywords. Returns category labels for PulseReport.event_flags.
9. **Top 5 headlines**: Limit to first 5 headlines for PulseReport.top_headlines.
10. **Language filter**: Only English articles (`language=en` param).

## Constraints

- All functions are `async def` (except `_score_text` and `_detect_events` which are pure computation).
- API key sourced from `config.settings.get_settings().NEWS_API_KEY` -- never hardcoded.
- Cache TTL is 300 seconds (5 minutes). `maxsize=64`.
- `httpx.AsyncClient` timeout is 10 seconds.
- Return `{}` (empty dict) on any error -- never raise to caller.
- NewsAPI requires `apiKey` as query parameter.
- `_fetch_articles` fetches `pageSize=20` articles by default.
- Sentiment score clamped to [-1.0, 1.0].
- Top headlines limited to 5.
- `_score_text` is case-insensitive matching.

## Test Requirements

All tests must mock `httpx.AsyncClient` -- no real network calls.

1. **News sentiment success**: Mock article response, assert returned dict has all 4 keys with correct values.
2. **Sentiment scoring positive**: Text with positive keywords -> positive score.
3. **Sentiment scoring negative**: Text with negative keywords -> negative score.
4. **Sentiment scoring neutral**: Text with no keywords -> 0.0.
5. **Sentiment scoring mixed**: Text with both positive and negative keywords -> balanced score.
6. **Event detection earnings**: Article with "earnings" in title -> ["earnings"] flag.
7. **Event detection multiple**: Articles with multiple event types -> all detected.
8. **Event detection none**: Articles with no event keywords -> [].
9. **Top headlines limited to 5**: Mock 20 articles, assert only 5 headlines returned.
10. **Total failure**: Mock API error, assert `{}`.
11. **Empty results**: Mock empty articles list, assert empty result with article_count=0.
12. **Cache hit**: Call `get_news_sentiment` twice, assert HTTP called only once.
13. **Settings injection**: Confirm API key from settings used in requests.
14. **Module singleton**: `from tools.news_connector import news` works.
15. **Close method**: `await news.close()` calls `client.aclose()`.
16. **Score text empty string**: `_score_text("")` returns 0.0.
17. **Score text None**: `_score_text(None)` returns 0.0.

## Acceptance Criteria

- [ ] `tools/news_connector.py` exists with `NewsConnector` class
- [ ] `get_news_sentiment()` async method returns sentiment_score, article_count, top_headlines, event_flags
- [ ] `_fetch_articles()` async method fetches from NewsAPI /v2/everything
- [ ] `_score_text()` method scores individual text for sentiment
- [ ] `_detect_events()` method detects event categories from articles
- [ ] `close()` async method for client cleanup
- [ ] TTLCache with maxsize=64, ttl=300
- [ ] httpx.AsyncClient with timeout=10.0
- [ ] API key from Settings (dependency injection)
- [ ] All external calls wrapped in try/except
- [ ] Returns {} on any error
- [ ] Sentiment score clamped to [-1.0, 1.0]
- [ ] Top headlines limited to 5
- [ ] Case-insensitive keyword matching
- [ ] Module-level `news` singleton
- [ ] All tests pass (`pytest tests/test_news_connector.py -v`)
- [ ] Ruff clean (`ruff check tools/news_connector.py`)
