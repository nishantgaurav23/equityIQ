"""Tests for agents/risk_guardian.py -- RiskGuardian specialist agent.

Covers US (Polygon + SPY benchmark) and India (Yahoo + Nifty50 benchmark)
paths, India-specific risk tools, and market routing.
"""

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

MOCK_BENCHMARK_DATA = {
    "prices": [3000.0, 3010.0, 3005.0, 3020.0, 3015.0, 3030.0, 3025.0, 3040.0, 3035.0, 3050.0],
    "volumes": [500_000_000] * 10,
    "dates": [f"2025-01-{i:02d}" for i in range(1, 11)],
}

MOCK_INDIA_VIX_DATA = {
    "prices": [14.5, 15.0, 14.8, 15.2, 14.9],
    "volumes": [0] * 5,
    "dates": ["2025-01-06", "2025-01-07", "2025-01-08", "2025-01-09", "2025-01-10"],
}


def _polygon_side_effect(ticker, days=365):
    """Return different data for stock vs SPY benchmark."""
    if ticker == "SPY":
        return MOCK_BENCHMARK_DATA
    return MOCK_PRICE_DATA


def _yahoo_side_effect(ticker, days=365):
    """Return different data for stock vs ^NSEI benchmark vs ^INDIAVIX."""
    if ticker == "^NSEI":
        return MOCK_BENCHMARK_DATA
    if ticker == "^INDIAVIX":
        return MOCK_INDIA_VIX_DATA
    return MOCK_PRICE_DATA


@pytest.fixture
def mock_polygon():
    """Patch the module-level _polygon connector."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(side_effect=_polygon_side_effect)
    with patch("agents.risk_guardian._polygon", mock_instance):
        yield mock_instance


@pytest.fixture
def mock_yahoo():
    """Patch the module-level _yahoo connector."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(side_effect=_yahoo_side_effect)
    with patch("agents.risk_guardian._yahoo", mock_instance):
        yield mock_instance


@pytest.fixture
def mock_polygon_error():
    """Patch _polygon to raise exceptions."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(side_effect=Exception("API down"))
    with patch("agents.risk_guardian._polygon", mock_instance):
        yield mock_instance


@pytest.fixture
def mock_yahoo_error():
    """Patch _yahoo to raise exceptions."""
    mock_instance = AsyncMock()
    mock_instance.get_price_history = AsyncMock(side_effect=Exception("API down"))
    with patch("agents.risk_guardian._yahoo", mock_instance):
        yield mock_instance


# ---------------------------------------------------------------------------
# T1: Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    """T1: RiskGuardian creates correctly with expected properties."""

    def test_creates_successfully(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent is not None

    def test_agent_name(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent.name == "risk_guardian"

    def test_output_schema(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert agent._output_schema is RiskGuardianReport

    def test_has_tools(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        assert len(agent._tools) >= 3

    def test_tool_names(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        tool_names = [fn.__name__ for fn in agent._tools]
        assert "get_price_history_tool" in tool_names
        assert "calc_risk_metrics_tool" in tool_names
        assert "get_india_market_risk_tool" in tool_names


# ---------------------------------------------------------------------------
# T2: Market routing -- get_price_history_tool
# ---------------------------------------------------------------------------


class TestMarketRouting:
    """T2: get_price_history_tool routes to correct connector."""

    @pytest.mark.asyncio
    async def test_us_ticker_uses_polygon(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("AAPL")
        mock_polygon.get_price_history.assert_awaited_once_with("AAPL", days=365)
        mock_yahoo.get_price_history.assert_not_awaited()
        assert len(result["prices"]) == 10

    @pytest.mark.asyncio
    async def test_indian_nse_ticker_uses_yahoo(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("RELIANCE.NS")
        mock_yahoo.get_price_history.assert_awaited_once_with("RELIANCE.NS", days=365)
        mock_polygon.get_price_history.assert_not_awaited()
        assert len(result["prices"]) == 10

    @pytest.mark.asyncio
    async def test_indian_bse_ticker_uses_yahoo(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_price_history_tool

        await get_price_history_tool("TCS.BO")
        mock_yahoo.get_price_history.assert_awaited_once_with("TCS.BO", days=365)
        mock_polygon.get_price_history.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_us_error_returns_empty(self, mock_polygon_error, mock_yahoo):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("BAD")
        assert result == {}

    @pytest.mark.asyncio
    async def test_india_error_returns_empty(self, mock_polygon, mock_yahoo_error):
        from agents.risk_guardian import get_price_history_tool

        result = await get_price_history_tool("BAD.NS")
        assert result == {}


# ---------------------------------------------------------------------------
# T3: calc_risk_metrics_tool -- US path
# ---------------------------------------------------------------------------


class TestCalcRiskMetricsUS:
    """T3: calc_risk_metrics_tool with US tickers uses SPY benchmark."""

    @pytest.mark.asyncio
    async def test_returns_all_metrics(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert "beta" in result
        assert "annualized_volatility" in result
        assert "sharpe_ratio" in result
        assert "max_drawdown" in result
        assert "var_95" in result
        assert "suggested_position_size" in result

    @pytest.mark.asyncio
    async def test_uses_spy_benchmark(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["benchmark_used"] == "SPY"

    @pytest.mark.asyncio
    async def test_uses_us_risk_free_rate(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["risk_free_rate_used"] == 0.05

    @pytest.mark.asyncio
    async def test_position_size_capped(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["suggested_position_size"] <= 0.10

    @pytest.mark.asyncio
    async def test_max_drawdown_negative_or_zero(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["max_drawdown"] <= 0.0

    @pytest.mark.asyncio
    async def test_volatility_non_negative(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result["annualized_volatility"] >= 0.0

    @pytest.mark.asyncio
    async def test_error_returns_empty(self, mock_polygon_error, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("BAD")
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_prices_returns_empty(self, mock_polygon, mock_yahoo):
        mock_polygon.get_price_history = AsyncMock(return_value={"prices": []})
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# T4: calc_risk_metrics_tool -- India path
# ---------------------------------------------------------------------------


class TestCalcRiskMetricsIndia:
    """T4: calc_risk_metrics_tool with Indian tickers uses Nifty50 benchmark."""

    @pytest.mark.asyncio
    async def test_returns_all_metrics(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("TCS.NS")
        assert "beta" in result
        assert "annualized_volatility" in result
        assert "sharpe_ratio" in result

    @pytest.mark.asyncio
    async def test_uses_nifty_benchmark(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("TCS.NS")
        assert result["benchmark_used"] == "^NSEI"

    @pytest.mark.asyncio
    async def test_uses_india_risk_free_rate(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        with patch(
            "agents.risk_guardian._get_risk_free_rate",
            AsyncMock(return_value=0.065),
        ):
            result = await calc_risk_metrics_tool("TCS.NS")
            assert result["risk_free_rate_used"] == 0.065

    @pytest.mark.asyncio
    async def test_position_size_capped(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("RELIANCE.NS")
        assert result["suggested_position_size"] <= 0.10

    @pytest.mark.asyncio
    async def test_bse_ticker_works(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        result = await calc_risk_metrics_tool("TCS.BO")
        assert result["benchmark_used"] == "^NSEI"


# ---------------------------------------------------------------------------
# T5: Benchmark fallback
# ---------------------------------------------------------------------------


class TestBenchmarkFallback:
    """T5: Beta defaults to 1.0 when benchmark data is unavailable."""

    @pytest.mark.asyncio
    async def test_benchmark_failure_defaults_beta_1(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        # Make SPY return empty data

        def _spy_fails(ticker, days=365):
            if ticker == "SPY":
                return {"prices": []}
            return MOCK_PRICE_DATA

        mock_polygon.get_price_history = AsyncMock(side_effect=_spy_fails)

        result = await calc_risk_metrics_tool("AAPL")
        assert result["beta"] == 1.0
        assert result["benchmark_used"] == "SPY"

    @pytest.mark.asyncio
    async def test_nifty_failure_defaults_beta_1(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import calc_risk_metrics_tool

        def _nifty_fails(ticker, days=365):
            if ticker == "^NSEI":
                return {"prices": []}
            return MOCK_PRICE_DATA

        mock_yahoo.get_price_history = AsyncMock(side_effect=_nifty_fails)

        result = await calc_risk_metrics_tool("TCS.NS")
        assert result["beta"] == 1.0
        assert result["benchmark_used"] == "^NSEI"


# ---------------------------------------------------------------------------
# T6: get_india_market_risk_tool
# ---------------------------------------------------------------------------


class TestIndiaMarketRiskTool:
    """T6: India-specific risk data tool."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_us_ticker(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_india_market_risk_tool

        result = await get_india_market_risk_tool("AAPL")
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_india_vix(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_india_market_risk_tool

        result = await get_india_market_risk_tool("RELIANCE.NS")
        assert "india_vix" in result
        assert result["india_vix"] == 14.9  # last price in MOCK_INDIA_VIX_DATA

    @pytest.mark.asyncio
    async def test_returns_circuit_breaker_band(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_india_market_risk_tool

        result = await get_india_market_risk_tool("TCS.NS")
        assert result["circuit_breaker_band"] == "10%/15%/20%"

    @pytest.mark.asyncio
    async def test_bse_ticker_works(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_india_market_risk_tool

        result = await get_india_market_risk_tool("TCS.BO")
        assert "circuit_breaker_band" in result

    @pytest.mark.asyncio
    async def test_vix_failure_still_returns_partial(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import get_india_market_risk_tool

        # Make VIX fetch fail
        def _vix_fails(ticker, days=365):
            if ticker == "^INDIAVIX":
                raise Exception("VIX unavailable")
            return MOCK_PRICE_DATA

        mock_yahoo.get_price_history = AsyncMock(side_effect=_vix_fails)

        result = await get_india_market_risk_tool("TCS.NS")
        # Should still have circuit breaker even if VIX fails
        assert "circuit_breaker_band" in result
        assert "india_vix" not in result


# ---------------------------------------------------------------------------
# T7: Analyze with mocked LLM
# ---------------------------------------------------------------------------


class TestAnalyze:
    """T7: analyze() returns a valid RiskGuardianReport with mocked LLM."""

    @pytest.mark.asyncio
    async def test_analyze_returns_risk_report(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        report_json = json.dumps(
            {
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
                "benchmark_used": "SPY",
                "risk_free_rate_used": 0.05,
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

                result = await agent.analyze("AAPL")

        assert isinstance(result, RiskGuardianReport)
        assert result.ticker == "AAPL"
        assert result.agent_name == "risk_guardian"
        assert result.signal == "BUY"
        assert result.confidence == 0.75
        assert result.beta == 0.85
        assert result.sharpe_ratio == 1.5
        assert result.suggested_position_size == 0.09
        assert result.benchmark_used == "SPY"
        assert result.risk_free_rate_used == 0.05

    @pytest.mark.asyncio
    async def test_analyze_india_report(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        report_json = json.dumps(
            {
                "ticker": "RELIANCE.NS",
                "agent_name": "risk_guardian",
                "signal": "BUY",
                "confidence": 0.70,
                "reasoning": "Moderate risk, Nifty-aligned beta",
                "beta": 1.1,
                "annualized_volatility": 0.28,
                "sharpe_ratio": 0.9,
                "max_drawdown": -0.18,
                "suggested_position_size": 0.07,
                "var_95": -0.03,
                "benchmark_used": "^NSEI",
                "risk_free_rate_used": 0.065,
                "india_vix": 14.9,
                "circuit_breaker_band": "10%/15%/20%",
                "fno_ban": False,
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

                result = await agent.analyze("RELIANCE.NS")

        assert isinstance(result, RiskGuardianReport)
        assert result.ticker == "RELIANCE.NS"
        assert result.benchmark_used == "^NSEI"
        assert result.risk_free_rate_used == 0.065
        assert result.india_vix == 14.9
        assert result.circuit_breaker_band == "10%/15%/20%"
        assert result.fno_ban is False

    @pytest.mark.asyncio
    async def test_analyze_sell_signal(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        report_json = json.dumps(
            {
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
                "benchmark_used": "SPY",
                "risk_free_rate_used": 0.05,
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

                result = await agent.analyze("TSLA")

        assert result.signal == "SELL"
        assert result.confidence == 0.80


# ---------------------------------------------------------------------------
# T8: Analyze fallback on error
# ---------------------------------------------------------------------------


class TestAnalyzeFallback:
    """T8: analyze() returns HOLD/0.0 fallback on errors."""

    @pytest.mark.asyncio
    async def test_fallback_on_runner_exception(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = Exception("Runner crashed")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await agent.analyze("AAPL")

        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_fallback_never_raises(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()

        with patch("agents.base_agent.Runner") as MockRunner:
            MockRunner.side_effect = RuntimeError("Unexpected error")

            with patch("agents.base_agent.InMemorySessionService") as MockSession:
                mock_session = MagicMock()
                mock_session.id = "test-session"
                MockSession.return_value.create_session = AsyncMock(return_value=mock_session)

                result = await agent.analyze("AAPL")
                assert result is not None


# ---------------------------------------------------------------------------
# T9: Agent card
# ---------------------------------------------------------------------------


class TestAgentCard:
    """T9: Agent card has correct structure."""

    def test_agent_card_name(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert card["name"] == "risk_guardian"

    def test_agent_card_output_schema(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert card["output_schema"] == "RiskGuardianReport"

    def test_agent_card_capabilities(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import RiskGuardian

        agent = RiskGuardian()
        card = agent.get_agent_card()
        assert "get_price_history_tool" in card["capabilities"]
        assert "calc_risk_metrics_tool" in card["capabilities"]
        assert "get_india_market_risk_tool" in card["capabilities"]


# ---------------------------------------------------------------------------
# T10: Factory and module instance
# ---------------------------------------------------------------------------


class TestFactory:
    """T10: Factory function and module-level instance."""

    def test_create_risk_guardian(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import create_risk_guardian

        agent = create_risk_guardian()
        assert agent.name == "risk_guardian"

    def test_module_level_instance(self, mock_polygon, mock_yahoo):
        from agents.risk_guardian import risk_guardian

        assert risk_guardian is not None
        assert risk_guardian.name == "risk_guardian"


# ---------------------------------------------------------------------------
# T11: Position size cap enforcement
# ---------------------------------------------------------------------------


class TestPositionSizeCap:
    """T11: Position size is always capped at 0.10."""

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


# ---------------------------------------------------------------------------
# T12: New RiskGuardianReport fields
# ---------------------------------------------------------------------------


class TestReportNewFields:
    """T12: RiskGuardianReport accepts new market-context and India fields."""

    def test_us_report_with_benchmark(self):
        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="risk_guardian",
            signal="BUY",
            confidence=0.8,
            reasoning="Low risk",
            benchmark_used="SPY",
            risk_free_rate_used=0.05,
        )
        assert report.benchmark_used == "SPY"
        assert report.risk_free_rate_used == 0.05
        assert report.india_vix is None
        assert report.fno_ban is None

    def test_india_report_with_all_fields(self):
        report = RiskGuardianReport(
            ticker="TCS.NS",
            agent_name="risk_guardian",
            signal="HOLD",
            confidence=0.7,
            reasoning="Moderate risk",
            benchmark_used="^NSEI",
            risk_free_rate_used=0.065,
            india_vix=15.2,
            circuit_breaker_band="10%/15%/20%",
            fno_ban=False,
        )
        assert report.benchmark_used == "^NSEI"
        assert report.risk_free_rate_used == 0.065
        assert report.india_vix == 15.2
        assert report.circuit_breaker_band == "10%/15%/20%"
        assert report.fno_ban is False

    def test_backward_compat_no_new_fields(self):
        """Old-style report without new fields still works."""
        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="risk_guardian",
            signal="BUY",
            confidence=0.8,
            reasoning="Test",
        )
        assert report.benchmark_used is None
        assert report.india_vix is None
        assert report.fno_ban is None
