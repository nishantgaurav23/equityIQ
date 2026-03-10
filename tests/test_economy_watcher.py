"""Tests for agents/economy_watcher.py -- EconomyWatcher specialist agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import EconomyReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_fred():
    """Patch the module-level connectors used by tool functions."""
    mock_us = AsyncMock()
    mock_us.get_macro_indicators = AsyncMock(
        return_value={
            "gdp_growth": 2.5,
            "inflation_rate": 3.1,
            "fed_funds_rate": 5.25,
            "unemployment_rate": 3.8,
            "macro_regime": "expansion",
        }
    )
    mock_india = AsyncMock()
    mock_india.get_macro_indicators = AsyncMock(
        return_value={
            "gdp_growth": 6.5,
            "inflation_rate": 5.2,
            "fed_funds_rate": 6.50,
            "unemployment_rate": 7.8,
            "macro_regime": "expansion",
        }
    )
    with (
        patch("agents.economy_watcher._us_connector", mock_us),
        patch("agents.economy_watcher._india_connector", mock_india),
        patch("agents.economy_watcher._current_ticker", "AAPL"),
    ):
        yield mock_us


@pytest.fixture
def mock_fred_error():
    """Patch connectors to raise on call (simulating errors)."""
    mock_us = AsyncMock()
    mock_us.get_macro_indicators = AsyncMock(side_effect=Exception("FRED API down"))
    mock_india = AsyncMock()
    mock_india.get_macro_indicators = AsyncMock(side_effect=Exception("API down"))
    with (
        patch("agents.economy_watcher._us_connector", mock_us),
        patch("agents.economy_watcher._india_connector", mock_india),
        patch("agents.economy_watcher._current_ticker", "AAPL"),
    ):
        yield mock_us


# ---------------------------------------------------------------------------
# T1: Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    """T1: EconomyWatcher creates correctly with expected properties."""

    def test_creates_successfully(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        assert watcher is not None

    def test_agent_name(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        assert watcher.name == "economy_watcher"

    def test_output_schema(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        assert watcher._output_schema is EconomyReport

    def test_has_tools(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        assert len(watcher._tools) >= 1

    def test_tool_names(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        tool_names = [fn.__name__ for fn in watcher._tools]
        assert "get_macro_indicators_tool" in tool_names


# ---------------------------------------------------------------------------
# T2: Tool Functions
# ---------------------------------------------------------------------------


class TestToolFunctions:
    """T2: Tool function calls FredConnector and handles errors."""

    @pytest.mark.asyncio
    async def test_get_macro_indicators_tool_calls_connector(self, mock_fred):
        from agents.economy_watcher import get_macro_indicators_tool

        result = await get_macro_indicators_tool()
        mock_fred.get_macro_indicators.assert_awaited_once()
        assert result["gdp_growth"] == 2.5
        assert result["macro_regime"] == "expansion"

    @pytest.mark.asyncio
    async def test_get_macro_indicators_tool_returns_all_fields(self, mock_fred):
        from agents.economy_watcher import get_macro_indicators_tool

        result = await get_macro_indicators_tool()
        assert "gdp_growth" in result
        assert "inflation_rate" in result
        assert "fed_funds_rate" in result
        assert "unemployment_rate" in result
        assert "macro_regime" in result

    @pytest.mark.asyncio
    async def test_get_macro_indicators_tool_exception_returns_empty(self, mock_fred_error):
        from agents.economy_watcher import get_macro_indicators_tool

        result = await get_macro_indicators_tool()
        assert result == {}


# ---------------------------------------------------------------------------
# T3: Analyze with mocked LLM
# ---------------------------------------------------------------------------


class TestAnalyze:
    """T3: analyze() returns a valid EconomyReport with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_returns_economy_report(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()

        report_json = json.dumps(
            {
                "ticker": "AAPL",
                "agent_name": "economy_watcher",
                "signal": "BUY",
                "confidence": 0.72,
                "reasoning": "Expansion regime favorable for tech stocks",
                "gdp_growth": 2.5,
                "inflation_rate": 3.1,
                "fed_funds_rate": 5.25,
                "unemployment_rate": 3.8,
                "macro_regime": "expansion",
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

                result = await watcher.analyze("AAPL")

        assert isinstance(result, EconomyReport)
        assert result.ticker == "AAPL"
        assert result.agent_name == "economy_watcher"
        assert result.signal == "BUY"
        assert result.confidence == 0.72
        assert result.gdp_growth == 2.5
        assert result.macro_regime == "expansion"

    @pytest.mark.asyncio
    async def test_analyze_sell_contraction(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()

        report_json = json.dumps(
            {
                "ticker": "TSLA",
                "agent_name": "economy_watcher",
                "signal": "SELL",
                "confidence": 0.65,
                "reasoning": "Contraction regime unfavorable for cyclical stocks",
                "gdp_growth": -1.2,
                "inflation_rate": 5.5,
                "fed_funds_rate": 5.50,
                "unemployment_rate": 5.1,
                "macro_regime": "contraction",
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

                result = await watcher.analyze("TSLA")

        assert result.signal == "SELL"
        assert result.macro_regime == "contraction"


# ---------------------------------------------------------------------------
# T4: Analyze fallback on error
# ---------------------------------------------------------------------------


class TestAnalyzeFallback:
    """T4: analyze() returns HOLD/0.0 fallback on errors."""

    @pytest.mark.asyncio
    async def test_fallback_on_runner_exception(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = Exception("Runner crashed")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await watcher.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = RuntimeError("Unexpected error")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await watcher.analyze("AAPL")
                assert result is not None


# ---------------------------------------------------------------------------
# T5: Agent card
# ---------------------------------------------------------------------------


class TestAgentCard:
    """T5: Agent card has correct structure."""

    def test_agent_card_name(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        card = watcher.get_agent_card()
        assert card["name"] == "economy_watcher"

    def test_agent_card_output_schema(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        card = watcher.get_agent_card()
        assert card["output_schema"] == "EconomyReport"

    def test_agent_card_capabilities(self, mock_fred):
        from agents.economy_watcher import EconomyWatcher

        watcher = EconomyWatcher()
        card = watcher.get_agent_card()
        assert "get_macro_indicators_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T6: Factory and module instance
# ---------------------------------------------------------------------------


class TestFactory:
    """T6: Factory function and module-level instance."""

    def test_create_economy_watcher(self, mock_fred):
        from agents.economy_watcher import create_economy_watcher

        watcher = create_economy_watcher()
        assert watcher.name == "economy_watcher"

    def test_module_level_instance(self, mock_fred):
        from agents.economy_watcher import economy_watcher

        assert economy_watcher is not None
        assert economy_watcher.name == "economy_watcher"
