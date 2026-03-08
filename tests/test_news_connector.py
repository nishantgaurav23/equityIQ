"""Tests for tools/news_connector.py -- NewsAPI async wrapper + sentiment scoring."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from config.settings import Settings


def _make_settings(**overrides) -> Settings:
    defaults = {"NEWS_API_KEY": "test-key-123"}
    defaults.update(overrides)
    return Settings(**defaults)


def _make_article(title: str = "Test headline", description: str = "Test desc") -> dict:
    return {
        "title": title,
        "description": description,
        "publishedAt": "2026-03-08T12:00:00Z",
    }


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


class TestNewsSentimentSuccess:
    @pytest.mark.asyncio
    async def test_returns_all_keys(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [
            _make_article("Stock surges on strong earnings", "Company beat expectations"),
            _make_article("Analysts upgrade rating", "Bullish outlook"),
            _make_article("Revenue growth exceeds forecast", "Positive results"),
        ]
        response = _mock_response(json_data={"articles": articles, "totalResults": 3})
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result = await connector.get_news_sentiment("AAPL")

        assert "sentiment_score" in result
        assert "article_count" in result
        assert "top_headlines" in result
        assert "event_flags" in result
        assert result["article_count"] == 3

    @pytest.mark.asyncio
    async def test_sentiment_score_in_range(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [_make_article("Stock surges", "Big gains")]
        response = _mock_response(json_data={"articles": articles, "totalResults": 1})
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result = await connector.get_news_sentiment("AAPL")

        assert -1.0 <= result["sentiment_score"] <= 1.0


class TestSentimentScoring:
    def test_positive_text(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        score = connector._score_text("Stock surges on strong growth and rally")
        assert score > 0.0

    def test_negative_text(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        score = connector._score_text("Stock plunges on weak earnings and loss warning")
        assert score < 0.0

    def test_neutral_text(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        score = connector._score_text("The company held a meeting today")
        assert score == 0.0

    def test_mixed_text(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        score = connector._score_text("Stock surges despite loss warning")
        # mixed: has both positive and negative keywords
        assert -1.0 <= score <= 1.0

    def test_empty_string(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        assert connector._score_text("") == 0.0

    def test_none_input(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        assert connector._score_text(None) == 0.0

    def test_case_insensitive(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        score_lower = connector._score_text("surge")
        score_upper = connector._score_text("SURGE")
        assert score_lower == score_upper
        assert score_lower > 0.0


class TestEventDetection:
    def test_earnings_detected(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [_make_article("Company reports earnings beat", "Strong quarterly results")]
        events = connector._detect_events(articles)
        assert "earnings" in events

    def test_multiple_events(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [
            _make_article("Earnings beat expectations", "Strong EPS"),
            _make_article("Company announces merger deal", "Acquisition complete"),
        ]
        events = connector._detect_events(articles)
        assert "earnings" in events
        assert "merger" in events

    def test_no_events(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [_make_article("Regular market update", "Nothing special")]
        events = connector._detect_events(articles)
        assert events == []


class TestTopHeadlines:
    @pytest.mark.asyncio
    async def test_limited_to_5(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [_make_article(f"Headline {i}") for i in range(20)]
        response = _mock_response(json_data={"articles": articles, "totalResults": 20})
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result = await connector.get_news_sentiment("AAPL")

        assert len(result["top_headlines"]) == 5


class TestFailureModes:
    @pytest.mark.asyncio
    async def test_api_error_returns_zero_count(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        response = _mock_response(status_code=500)
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result = await connector.get_news_sentiment("AAPL")

        # API error at fetch level -> empty articles -> zero-count result
        assert result["article_count"] == 0
        assert result["sentiment_score"] == 0.0

    @pytest.mark.asyncio
    async def test_exception_returns_zero_count(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        result = await connector.get_news_sentiment("AAPL")

        # Network exception at fetch level -> empty articles -> zero-count result
        assert result["article_count"] == 0
        assert result["sentiment_score"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_articles_returns_zero_count(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        response = _mock_response(json_data={"articles": [], "totalResults": 0})
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result = await connector.get_news_sentiment("AAPL")

        assert result["article_count"] == 0
        assert result["sentiment_score"] == 0.0
        assert result["top_headlines"] == []
        assert result["event_flags"] == []


class TestCacheHit:
    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        articles = [_make_article("Test headline")]
        response = _mock_response(json_data={"articles": articles, "totalResults": 1})
        connector.client = AsyncMock()
        connector.client.get = AsyncMock(return_value=response)

        result1 = await connector.get_news_sentiment("AAPL")
        result2 = await connector.get_news_sentiment("AAPL")

        assert result1 == result2
        connector.client.get.assert_called_once()


class TestSettingsInjection:
    def test_api_key_from_settings(self):
        from tools.news_connector import NewsConnector

        settings = _make_settings(NEWS_API_KEY="my-custom-key")
        connector = NewsConnector(settings=settings)
        assert connector.api_key == "my-custom-key"


class TestModuleSingleton:
    def test_singleton_importable(self):
        from tools.news_connector import news

        assert news is not None
        assert hasattr(news, "get_news_sentiment")


class TestCloseMethod:
    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        from tools.news_connector import NewsConnector

        connector = NewsConnector(settings=_make_settings())
        connector.client = AsyncMock()

        await connector.close()

        connector.client.aclose.assert_called_once()
