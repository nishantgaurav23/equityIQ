"""Tests for agents/valuation_scout.py -- ValuationScout specialist agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import ValuationReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_polygon():
    """Patch the module-level _connector used by tool functions."""
    mock_instance = AsyncMock()
    mock_instance.get_fundamentals = AsyncMock(
        return_value={
            "pe_ratio": 25.3,
            "pb_ratio": 12.1,
            "revenue_growth": 0.08,
            "debt_to_equity": 1.5,
            "fcf_yield": 0.04,
        }
    )
    mock_instance.get_price_history = AsyncMock(
        return_value={
            "prices": [150.0, 152.0, 155.0],
            "volumes": [1000000, 1200000, 1100000],
            "dates": ["2025-01-01", "2025-01-02", "2025-01-03"],
        }
    )
    with patch("agents.valuation_scout._polygon", mock_instance):
        yield mock_instance


@pytest.fixture
def mock_polygon_error():
    """Patch _polygon to return empty dicts (simulating errors)."""
    mock_instance = AsyncMock()
    mock_instance.get_fundamentals = AsyncMock(return_value={})
    mock_instance.get_price_history = AsyncMock(return_value={})
    with patch("agents.valuation_scout._polygon", mock_instance):
        yield mock_instance


# ---------------------------------------------------------------------------
# T1: Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    """T1: ValuationScout creates correctly with expected properties."""

    def test_creates_successfully(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        assert scout is not None

    def test_agent_name(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        assert scout.name == "valuation_scout"

    def test_output_schema(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        assert scout._output_schema is ValuationReport

    def test_has_tools(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        assert len(scout._tools) >= 2

    def test_tool_names(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        tool_names = [fn.__name__ for fn in scout._tools]
        assert "get_fundamentals_tool" in tool_names
        assert "get_price_history_tool" in tool_names


# ---------------------------------------------------------------------------
# T2: Tool Functions
# ---------------------------------------------------------------------------


class TestToolFunctions:
    """T2: Tool functions call PolygonConnector and handle errors."""

    @pytest.mark.asyncio
    async def test_get_fundamentals_tool_calls_connector(self, mock_polygon):
        from agents.valuation_scout import get_fundamentals_tool

        result = await get_fundamentals_tool("AAPL")
        mock_polygon.get_fundamentals.assert_awaited_once_with("AAPL")
        assert result["pe_ratio"] == 25.3

    @pytest.mark.asyncio
    async def test_get_price_history_tool_calls_connector(self, mock_polygon):
        from agents.valuation_scout import get_price_history_tool

        result = await get_price_history_tool("AAPL")
        mock_polygon.get_price_history.assert_awaited_once_with("AAPL", days=365)
        assert len(result["prices"]) == 3

    @pytest.mark.asyncio
    async def test_get_fundamentals_tool_error_returns_empty(self, mock_polygon_error):
        from agents.valuation_scout import get_fundamentals_tool

        result = await get_fundamentals_tool("BAD")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_price_history_tool_error_returns_empty(self, mock_polygon_error):
        from agents.valuation_scout import get_price_history_tool

        result = await get_price_history_tool("BAD")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_fundamentals_routes_indian_ticker_to_yahoo(self):
        """Indian ticker (.NS) routes to YahooConnector."""
        from agents.valuation_scout import get_fundamentals_tool

        mock_yahoo = AsyncMock()
        mock_yahoo.get_fundamentals = AsyncMock(return_value={"pe_ratio": 30.0, "pb_ratio": 5.0})
        with patch("agents.valuation_scout._yahoo", mock_yahoo):
            result = await get_fundamentals_tool("TCS.NS")
        mock_yahoo.get_fundamentals.assert_awaited_once_with("TCS.NS")
        assert result["pe_ratio"] == 30.0

    @pytest.mark.asyncio
    async def test_get_price_history_routes_indian_ticker_to_yahoo(self):
        """Indian ticker (.BO) routes to YahooConnector for price history."""
        from agents.valuation_scout import get_price_history_tool

        mock_yahoo = AsyncMock()
        mock_yahoo.get_price_history = AsyncMock(
            return_value={
                "prices": [2000.0, 2010.0],
                "volumes": [500000, 600000],
                "dates": ["2025-01-01", "2025-01-02"],
                "currency": "INR",
            }
        )
        with patch("agents.valuation_scout._yahoo", mock_yahoo):
            result = await get_price_history_tool("RELIANCE.BO")
        mock_yahoo.get_price_history.assert_awaited_once_with("RELIANCE.BO", days=365)
        assert result["currency"] == "INR"

    @pytest.mark.asyncio
    async def test_get_fundamentals_tool_exception_returns_empty(self, mock_polygon):
        mock_polygon.get_fundamentals = AsyncMock(side_effect=Exception("API down"))
        from agents.valuation_scout import get_fundamentals_tool

        result = await get_fundamentals_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_price_history_tool_exception_returns_empty(self, mock_polygon):
        mock_polygon.get_price_history = AsyncMock(side_effect=Exception("API down"))
        from agents.valuation_scout import get_price_history_tool

        result = await get_price_history_tool("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# T3: Analyze with mocked LLM
# ---------------------------------------------------------------------------


class TestAnalyze:
    """T3: analyze() returns a valid ValuationReport with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_returns_valuation_report(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()

        report_json = json.dumps(
            {
                "ticker": "AAPL",
                "agent_name": "valuation_scout",
                "signal": "BUY",
                "confidence": 0.85,
                "reasoning": "Strong fundamentals, undervalued by 15%",
                "pe_ratio": 25.3,
                "pb_ratio": 12.1,
                "revenue_growth": 0.08,
                "debt_to_equity": 1.5,
                "fcf_yield": 0.04,
                "intrinsic_value_gap": 0.15,
            }
        )

        # Mock the runner to return a valid report
        mock_part = MagicMock()
        mock_part.text = report_json

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
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await scout.analyze("AAPL")

        assert isinstance(result, ValuationReport)
        assert result.ticker == "AAPL"
        assert result.agent_name == "valuation_scout"
        assert result.signal == "BUY"
        assert result.confidence == 0.85
        assert result.pe_ratio == 25.3
        assert result.intrinsic_value_gap == 0.15

    @pytest.mark.asyncio
    async def test_analyze_hold_signal(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()

        report_json = json.dumps(
            {
                "ticker": "MSFT",
                "agent_name": "valuation_scout",
                "signal": "HOLD",
                "confidence": 0.5,
                "reasoning": "Fairly valued, mixed signals",
                "pe_ratio": 30.0,
                "intrinsic_value_gap": 0.0,
            }
        )

        mock_part = MagicMock()
        mock_part.text = report_json

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
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await scout.analyze("MSFT")

        assert result.signal == "HOLD"
        assert result.confidence == 0.5


# ---------------------------------------------------------------------------
# T4: Analyze fallback on error
# ---------------------------------------------------------------------------


class TestAnalyzeFallback:
    """T4: analyze() returns HOLD/0.0 fallback on errors."""

    @pytest.mark.asyncio
    async def test_fallback_on_runner_exception(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = Exception("Runner crashed")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await scout.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = RuntimeError("Unexpected error")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                # Should not raise
                result = await scout.analyze("AAPL")
                assert result is not None


# ---------------------------------------------------------------------------
# T5: Agent card
# ---------------------------------------------------------------------------


class TestAgentCard:
    """T5: Agent card has correct structure."""

    def test_agent_card_name(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        card = scout.get_agent_card()
        assert card["name"] == "valuation_scout"

    def test_agent_card_output_schema(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        card = scout.get_agent_card()
        assert card["output_schema"] == "ValuationReport"

    def test_agent_card_capabilities(self, mock_polygon):
        from agents.valuation_scout import ValuationScout

        scout = ValuationScout()
        card = scout.get_agent_card()
        assert "get_fundamentals_tool" in card["capabilities"]
        assert "get_price_history_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T6: Factory and module instance
# ---------------------------------------------------------------------------


class TestFactory:
    """T6: Factory function and module-level instance."""

    def test_create_valuation_scout(self, mock_polygon):
        from agents.valuation_scout import create_valuation_scout

        scout = create_valuation_scout()
        assert scout.name == "valuation_scout"

    def test_module_level_instance(self, mock_polygon):
        from agents.valuation_scout import valuation_scout

        assert valuation_scout is not None
        assert valuation_scout.name == "valuation_scout"
