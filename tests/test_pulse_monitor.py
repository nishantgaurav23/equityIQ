"""Tests for PulseMonitor agent (S7.3).

Tests cover: tool functions, agent instantiation, agent card, analyze success,
analyze fallback, and confidence cap enforcement.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import PulseReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_news_connector():
    """Patch the module-level _news_connector in pulse_monitor."""
    with patch("agents.pulse_monitor._news_connector") as mock:
        mock.get_news_sentiment = AsyncMock(return_value={
            "sentiment_score": 0.45,
            "article_count": 5,
            "top_headlines": [
                "AAPL beats earnings expectations",
                "Apple launches new product",
                "Apple stock surges on strong guidance",
                "Analysts upgrade AAPL",
                "Apple AI strategy impresses Wall Street",
            ],
            "event_flags": ["earnings", "product_launch"],
        })
        yield mock


@pytest.fixture()
def mock_polygon_connector():
    """Patch the module-level _polygon_connector in pulse_monitor."""
    with patch("agents.pulse_monitor._polygon_connector") as mock:
        mock.get_company_news = AsyncMock(return_value={
            "headlines": ["Apple Q4 results top estimates", "AAPL rises 3%"],
            "articles": [
                {"title": "Apple Q4 results top estimates", "published_utc": "2025-01-15"},
                {"title": "AAPL rises 3%", "published_utc": "2025-01-14"},
            ],
        })
        yield mock


@pytest.fixture()
def mock_news_error():
    """Patch _news_connector to raise an exception."""
    with patch("agents.pulse_monitor._news_connector") as mock:
        mock.get_news_sentiment = AsyncMock(side_effect=Exception("API down"))
        yield mock


@pytest.fixture()
def mock_polygon_error():
    """Patch _polygon_connector to raise an exception."""
    with patch("agents.pulse_monitor._polygon_connector") as mock:
        mock.get_company_news = AsyncMock(side_effect=Exception("API down"))
        yield mock


# ---------------------------------------------------------------------------
# T2: Tool Functions
# ---------------------------------------------------------------------------

class TestGetNewsSentimentTool:
    """Tests for get_news_sentiment_tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_news_connector):
        from agents.pulse_monitor import get_news_sentiment_tool

        result = await get_news_sentiment_tool("AAPL")

        mock_news_connector.get_news_sentiment.assert_awaited_once_with("AAPL")
        assert result["sentiment_score"] == 0.45
        assert result["article_count"] == 5
        assert len(result["top_headlines"]) == 5
        assert "earnings" in result["event_flags"]

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_news_error):
        from agents.pulse_monitor import get_news_sentiment_tool

        result = await get_news_sentiment_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_never_raises(self, mock_news_error):
        from agents.pulse_monitor import get_news_sentiment_tool

        # Should not raise, just return {}
        result = await get_news_sentiment_tool("AAPL")
        assert isinstance(result, dict)


class TestGetCompanyNewsTool:
    """Tests for get_company_news_tool."""

    @pytest.mark.asyncio
    async def test_success(self, mock_polygon_connector):
        from agents.pulse_monitor import get_company_news_tool

        result = await get_company_news_tool("AAPL")

        mock_polygon_connector.get_company_news.assert_awaited_once_with("AAPL")
        assert "headlines" in result
        assert len(result["headlines"]) == 2

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_polygon_error):
        from agents.pulse_monitor import get_company_news_tool

        result = await get_company_news_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_never_raises(self, mock_polygon_error):
        from agents.pulse_monitor import get_company_news_tool

        result = await get_company_news_tool("AAPL")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# T3: Agent Class
# ---------------------------------------------------------------------------

class TestPulseMonitorAgent:
    """Tests for PulseMonitorAgent instantiation and properties."""

    def test_instantiation(self):
        from agents.pulse_monitor import PulseMonitorAgent

        agent = PulseMonitorAgent()
        assert agent.name == "pulse_monitor"

    def test_output_schema(self):
        from agents.pulse_monitor import PulseMonitorAgent

        agent = PulseMonitorAgent()
        assert agent._output_schema is PulseReport

    def test_inherits_base(self):
        from agents.base_agent import BaseAnalystAgent
        from agents.pulse_monitor import PulseMonitorAgent

        assert issubclass(PulseMonitorAgent, BaseAnalystAgent)

    def test_has_two_tools(self):
        from agents.pulse_monitor import PulseMonitorAgent

        agent = PulseMonitorAgent()
        assert len(agent._tools) == 2


class TestAgentCard:
    """Tests for get_agent_card()."""

    def test_card_has_name(self):
        from agents.pulse_monitor import PulseMonitorAgent

        card = PulseMonitorAgent().get_agent_card()
        assert card["name"] == "pulse_monitor"

    def test_card_has_output_schema(self):
        from agents.pulse_monitor import PulseMonitorAgent

        card = PulseMonitorAgent().get_agent_card()
        assert card["output_schema"] == "PulseReport"

    def test_card_has_capabilities(self):
        from agents.pulse_monitor import PulseMonitorAgent

        card = PulseMonitorAgent().get_agent_card()
        assert "get_news_sentiment_tool" in card["capabilities"]
        assert "get_company_news_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T4: Module Exports
# ---------------------------------------------------------------------------

class TestModuleExports:
    """Tests for module-level exports."""

    def test_module_level_instance(self):
        from agents.pulse_monitor import pulse_monitor

        assert pulse_monitor is not None
        assert pulse_monitor.name == "pulse_monitor"

    def test_factory_function(self):
        from agents.pulse_monitor import create_pulse_monitor

        agent = create_pulse_monitor()
        assert agent.name == "pulse_monitor"


# ---------------------------------------------------------------------------
# T5: Analyze Success (mocked LLM)
# ---------------------------------------------------------------------------

class TestAnalyzeSuccess:
    """Test analyze() with mocked LLM returning valid PulseReport."""

    @pytest.mark.asyncio
    async def test_analyze_returns_pulse_report(self):
        from agents.pulse_monitor import PulseMonitorAgent

        report_data = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.75,
            reasoning="Strong positive sentiment with earnings beat.",
            sentiment_score=0.45,
            article_count=5,
            top_headlines=[
                "AAPL beats earnings",
                "Apple launches new product",
                "Apple stock surges",
            ],
            event_flags=["earnings", "product_launch"],
        )

        agent = PulseMonitorAgent()

        mock_part = MagicMock()
        mock_part.text = report_data.model_dump_json()

        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def fake_run_async(**kwargs):
            yield mock_event

        with patch("agents.base_agent.Runner") as MockRunner:
            runner_instance = MagicMock()
            runner_instance.run_async = fake_run_async
            MockRunner.return_value = runner_instance

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )

                result = await agent.analyze("AAPL")

        assert isinstance(result, PulseReport)
        assert result.ticker == "AAPL"
        assert result.signal == "BUY"
        assert result.sentiment_score == 0.45
        assert result.article_count == 5
        assert "earnings" in result.event_flags


# ---------------------------------------------------------------------------
# T6: Analyze Fallback
# ---------------------------------------------------------------------------

class TestAnalyzeFallback:
    """Test analyze() fallback on error."""

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        from agents.pulse_monitor import PulseMonitorAgent

        agent = PulseMonitorAgent()

        with (
            patch(
                "agents.base_agent.Runner",
                side_effect=Exception("LLM unavailable"),
            ),
            patch("agents.base_agent.InMemorySessionService"),
        ):
            result = await agent.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert result.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self):
        from agents.pulse_monitor import PulseMonitorAgent

        agent = PulseMonitorAgent()

        with (
            patch(
                "agents.base_agent.Runner",
                side_effect=RuntimeError("crash"),
            ),
            patch("agents.base_agent.InMemorySessionService"),
        ):
            # Should not raise
            result = await agent.analyze("AAPL")
            assert result is not None


# ---------------------------------------------------------------------------
# T7: Confidence Cap (PulseReport validator)
# ---------------------------------------------------------------------------

class TestConfidenceCap:
    """Verify PulseReport caps confidence at 0.70 when article_count < 3."""

    def test_cap_applied_low_articles(self):
        report = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.90,
            reasoning="Test",
            sentiment_score=0.5,
            article_count=2,
        )
        assert report.confidence == 0.70

    def test_no_cap_sufficient_articles(self):
        report = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.90,
            reasoning="Test",
            sentiment_score=0.5,
            article_count=5,
        )
        assert report.confidence == 0.90

    def test_cap_at_boundary(self):
        report = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.70,
            reasoning="Test",
            sentiment_score=0.5,
            article_count=2,
        )
        assert report.confidence == 0.70

    def test_below_cap_unchanged(self):
        report = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.50,
            reasoning="Test",
            sentiment_score=0.5,
            article_count=1,
        )
        assert report.confidence == 0.50

    def test_exactly_3_articles_no_cap(self):
        report = PulseReport(
            ticker="AAPL",
            agent_name="pulse_monitor",
            signal="BUY",
            confidence=0.85,
            reasoning="Test",
            sentiment_score=0.5,
            article_count=3,
        )
        assert report.confidence == 0.85


