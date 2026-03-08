"""Tests for agents/risk_guardian.py -- RiskGuardian specialist agent."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import RiskGuardianReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_PRICE_DATA = {
    "prices": [100.0, 102.0, 101.0, 105.0, 103.0, 107.0, 106.0, 110.0, 108.0, 112.0],
    "volumes": [1_000_000] * 10,
    "dates": [f"2025-01-{i:02d}" for i in range(1, 11)],
}


@pytest.fixture
def mock_polygon():
    """Patch the module-level _connector used by tool functions."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(return_value=MOCK_PRICE_DATA)
    with patch("agents.risk_guardian._connector", mock_instance):
        yield mock_instance


@pytest.fixture
def mock_polygon_error():
    """Patch _connector to raise exceptions."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(side_effect=Exception("API down"))
    with patch("agents.risk_guardian._connector", mock_instance):
        yield mock_instance


# ---------------------------------------------------------------------------
# T1: Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    """T1: RiskGuardian creates correctly with expected properties."""

    def test_creates_successfully(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent is not None

    def test_agent_name(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent.name == "risk_guardian"

    def test_output_schema(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent._output_schema is RiskGuardianReport

    def test_has_tools(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert len(agent._tools) >= 2

    def test_tool_names(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        tool_names = [fn.__name__ for fn in agent._tools]
        assert "get_price_history_tool" in tool_names
        assert "calc_risk_metrics_tool" in tool_names


# ---------------------------------------------------------------------------
# T2: get_price_history_tool
# ---------------------------------------------------------------------------


class TestGetPriceHistoryTool:
    """T2: get_price_history_tool calls PolygonConnector and handles errors."""

    @pytest.mark.asyncio
    async def test_calls_connector(self, mock_polygon):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("AAPL")
        mock_polygon.get_price_history.assert_awaited_once_with("AAPL", days=365)
        assert len(result["prices"]) == 10

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, mock_polygon_error):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("BAD")
        assert result == {}


# ---------------------------------------------------------------------------
# T3: calc_risk_metrics_tool
# ---------------------------------------------------------------------------


class TestCalcRiskMetricsTool:
    """T3: calc_risk_metrics_tool fetches data and computes risk metrics."""

    @pytest.mark.asyncio
    async def test_returns_all_metrics(self, mock_polygon):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert "beta" in result
        assert "annualized_volatility" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "var_95" in result
        assert "suggested_position_size" in result

    @pytest.mark.asyncio
    async def test_position_size_capped(self, mock_polygon):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["suggested_position_size"] <= 0.10

    @pytest.mark.asyncio
    async def test_max_drawdown_negative_or_zero(self, mock_polygon):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["max_drawdown"] <= 0.0

    @pytest.mark.asyncio
    async def test_volatility_non_negative(self, mock_polygon):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["annualized_volatility"] >= 0.0

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_polygon_error):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("BAD")
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_prices_returns_empty(self, mock_polygon):
        mock_polygon.get_price_history = AsyncMock(return_value={"prices": []})
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# T4: Analyze with mocked LLM
# ---------------------------------------------------------------------------


class TestAnalyze:
    """T4: analyze() returns a valid RiskGuardianReport with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_returns_risk_report(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        report_json = json.dumps({
            "ticker": "AAPL",
            "agent_name": "risk_guardian",
            "signal": "BUY",
            "confidence": 0.75,
            "reasoning": "Low risk profile, good Sharpe ratio",
            "beta": 0.85,
            "annualized_volatility": 0.22,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.15,
            "suggested_position_size": 0.09,
            "var_95": -0.025,
        })

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
                MockSession.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )

                result = await agent.analyze("AAPL")

        assert isinstance(result, RiskGuardianReport)
        assert result.ticker == "AAPL"
        assert result.agent_name == "risk_guardian"
        assert result.signal == "BUY"
        assert result.confidence == 0.75
        assert result.beta == 0.85
        assert result.sharpe_ratio == 1.5
        assert result.suggested_position_size == 0.09

    @pytest.mark.asyncio
    async def test_analyze_sell_signal(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        report_json = json.dumps({
            "ticker": "TSLA",
            "agent_name": "risk_guardian",
            "signal": "SELL",
            "confidence": 0.80,
            "reasoning": "High risk: elevated beta and volatility",
            "beta": 1.8,
            "annualized_volatility": 0.55,
            "sharpe_ratio": -0.2,
            "max_drawdown": -0.45,
            "suggested_position_size": 0.04,
            "var_95": -0.05,
        })

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
                MockSession.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )

                result = await agent.analyze("TSLA")

        assert result.signal == "SELL"
        assert result.confidence == 0.80


# ---------------------------------------------------------------------------
# T5: Analyze fallback on error
# ---------------------------------------------------------------------------


class TestAnalyzeFallback:
    """T5: analyze() returns HOLD/0.0 fallback on errors."""

    @pytest.mark.asyncio
    async def test_fallback_on_runner_exception(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = Exception("Runner crashed")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )

                result = await agent.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = RuntimeError("Unexpected error")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(
                    return_value=mock_session
                )

                result = await agent.analyze("AAPL")
                assert result is not None


# ---------------------------------------------------------------------------
# T6: Agent card
# ---------------------------------------------------------------------------


class TestAgentCard:
    """T6: Agent card has correct structure."""

    def test_agent_card_name(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert card["name"] == "risk_guardian"

    def test_agent_card_output_schema(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert card["output_schema"] == "RiskGuardianReport"

    def test_agent_card_capabilities(self, mock_polygon):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert "get_price_history_tool" in card["capabilities"]
        assert "calc_risk_metrics_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T7: Factory and module instance
# ---------------------------------------------------------------------------


class TestFactory:
    """T7: Factory function and module-level instance."""

    def test_create_risk_guardian(self, mock_polygon):
        from agents.risk_guardian import create_risk_guardian

        agent = create_risk_guardian()
        assert agent.name == "risk_guardian"

    def test_module_level_instance(self, mock_polygon):
        from agents.risk_guardian import risk_guardian

        assert risk_guardian is not None
        assert risk_guardian.name == "risk_guardian"


# ---------------------------------------------------------------------------
# T8: Position size cap enforcement
# ---------------------------------------------------------------------------


class TestPositionSizeCap:
    """T8: Position size is always capped at 0.10."""

    def test_report_validator_caps_position_size(self):
        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="risk_guardian",
            signal="BUY",
            confidence=0.8,
            reasoning="Test",
            suggested_position_size=0.50,
        )
        assert report.suggested_position_size == 0.10

    def test_report_validator_allows_valid_size(self):
        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="risk_guardian",
            signal="BUY",
            confidence=0.8,
            reasoning="Test",
            suggested_position_size=0.05,
        )
        assert report.suggested_position_size == 0.05

    def test_report_validator_clamps_negative(self):
        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="risk_guardian",
            signal="BUY",
            confidence=0.8,
            reasoning="Test",
            suggested_position_size=-0.05,
        )
        assert report.suggested_position_size == 0.0
