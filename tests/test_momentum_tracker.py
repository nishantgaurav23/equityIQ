"""Tests for agents/momentum_tracker.py -- S7.2 Momentum Tracker Agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import AnalystReport, MomentumReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_price_data(n: int = 250, base: float = 100.0, trend: float = 0.5):
    """Generate synthetic price/volume data for testing."""
    import random
    random.seed(42)
    prices = []
    volumes = []
    p = base
    for _ in range(n):
        p += trend + random.gauss(0, 2)
        prices.append(round(p, 2))
        volumes.append(random.randint(1_000_000, 5_000_000))
    dates = [f"2025-{(i // 30 + 1):02d}-{(i % 28 + 1):02d}" for i in range(n)]
    return {"prices": prices, "volumes": volumes, "dates": dates}


def _make_bearish_data(n: int = 250):
    """Generate bearish price data (downtrend)."""
    return _make_price_data(n=n, base=200.0, trend=-0.8)


def _make_stable_volume_data(n: int = 250):
    """Generate data with stable volume."""
    data = _make_price_data(n=n)
    # Make all volumes identical so trend is stable
    avg_vol = 2_000_000
    data["volumes"] = [avg_vol] * n
    return data


# ---------------------------------------------------------------------------
# Tool Function Tests
# ---------------------------------------------------------------------------

class TestGetTechnicalAnalysis:
    """Tests for the get_technical_analysis tool function."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Test successful analysis with valid price data."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert "rsi_14" in result
        assert "macd_signal" in result
        assert "above_sma_50" in result
        assert "above_sma_200" in result
        assert "volume_trend" in result
        assert "price_momentum_score" in result
        assert result["rsi_14"] is not None
        assert isinstance(result["above_sma_50"], bool)
        assert isinstance(result["above_sma_200"], bool)

    @pytest.mark.asyncio
    async def test_empty_prices(self):
        """Test with empty price history from Polygon."""
        from agents.momentum_tracker import get_technical_analysis

        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value={})

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["rsi_14"] is None
        assert result["macd_signal"] is None
        assert result["above_sma_50"] is None
        assert result["above_sma_200"] is None
        assert result["volume_trend"] is None
        assert result["price_momentum_score"] is None

    @pytest.mark.asyncio
    async def test_polygon_error(self):
        """Test Polygon connector raising an exception."""
        from agents.momentum_tracker import get_technical_analysis

        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(side_effect=Exception("API down"))

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["rsi_14"] is None
        assert result["price_momentum_score"] is None

    @pytest.mark.asyncio
    async def test_rsi_calculation(self):
        """Verify RSI is computed from price data."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["rsi_14"] is not None
        assert 0.0 <= result["rsi_14"] <= 100.0

    @pytest.mark.asyncio
    async def test_macd_calculation(self):
        """Verify MACD signal value is extracted."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["macd_signal"] is not None
        assert isinstance(result["macd_signal"], float)

    @pytest.mark.asyncio
    async def test_sma_crossover_above(self):
        """Price above both SMAs -> both flags True."""
        from agents.momentum_tracker import get_technical_analysis

        # Strong uptrend so price is above both SMAs
        price_data = _make_price_data(n=250, base=100.0, trend=1.0)
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["above_sma_50"] is True
        assert result["above_sma_200"] is True

    @pytest.mark.asyncio
    async def test_sma_crossover_below(self):
        """Price below both SMAs -> both flags False."""
        from agents.momentum_tracker import get_technical_analysis

        # Strong downtrend
        price_data = _make_bearish_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["above_sma_50"] is False
        assert result["above_sma_200"] is False

    @pytest.mark.asyncio
    async def test_sma_crossover_mixed(self):
        """Test that SMA crossover can produce mixed results."""
        from agents.momentum_tracker import get_technical_analysis

        # Create data where price recently crossed above SMA50 but not SMA200
        # Start bearish then turn bullish recently
        import random
        random.seed(42)
        prices = []
        p = 200.0
        for i in range(250):
            if i < 200:
                p -= 0.3 + random.gauss(0, 1)
            else:
                p += 2.0 + random.gauss(0, 1)
            prices.append(round(p, 2))
        volumes = [2_000_000] * 250
        dates = [f"2025-01-{(i % 28 + 1):02d}" for i in range(250)]
        price_data = {"prices": prices, "volumes": volumes, "dates": dates}

        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        # At least one should differ from the other (mixed signals)
        assert result["above_sma_50"] is not None
        assert result["above_sma_200"] is not None

    @pytest.mark.asyncio
    async def test_volume_trend_increasing(self):
        """Recent volume > 1.2x average -> 'increasing'."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data()
        # Make last 10 days volume much higher than prior 30
        price_data["volumes"][-10:] = [10_000_000] * 10
        price_data["volumes"][-40:-10] = [1_000_000] * 30

        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["volume_trend"] == "increasing"

    @pytest.mark.asyncio
    async def test_volume_trend_decreasing(self):
        """Recent volume < 0.8x average -> 'decreasing'."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data()
        # Make last 10 days volume much lower than prior 30
        price_data["volumes"][-10:] = [100_000] * 10
        price_data["volumes"][-40:-10] = [5_000_000] * 30

        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["volume_trend"] == "decreasing"

    @pytest.mark.asyncio
    async def test_volume_trend_stable(self):
        """Neutral volume -> 'stable'."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_stable_volume_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["volume_trend"] == "stable"

    @pytest.mark.asyncio
    async def test_momentum_score_bullish(self):
        """Bullish indicators -> positive momentum score."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data(n=250, base=50.0, trend=1.0)
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["price_momentum_score"] is not None
        assert result["price_momentum_score"] > 0.0

    @pytest.mark.asyncio
    async def test_momentum_score_bearish(self):
        """Bearish indicators -> negative momentum score."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_bearish_data()
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert result["price_momentum_score"] is not None
        assert result["price_momentum_score"] < 0.0

    @pytest.mark.asyncio
    async def test_momentum_score_clamped(self):
        """Score stays in [-1.0, 1.0]."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = _make_price_data(n=250, base=10.0, trend=5.0)
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        assert -1.0 <= result["price_momentum_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        """Fewer than 15 prices -> RSI defaults to 50."""
        from agents.momentum_tracker import get_technical_analysis

        price_data = {"prices": [100.0] * 10, "volumes": [1_000_000] * 10, "dates": ["2025-01-01"] * 10}
        mock_connector = MagicMock()
        mock_connector.get_price_history = AsyncMock(return_value=price_data)

        with patch("agents.momentum_tracker.PolygonConnector", return_value=mock_connector):
            result = await get_technical_analysis("AAPL")

        # RSI should be 50.0 (insufficient data default)
        assert result["rsi_14"] == 50.0


# ---------------------------------------------------------------------------
# Agent Tests
# ---------------------------------------------------------------------------

class TestMomentumTrackerAgent:
    """Tests for the MomentumTrackerAgent class."""

    def test_agent_class_is_base_analyst(self):
        """MomentumTrackerAgent inherits BaseAnalystAgent."""
        from agents.base_agent import BaseAnalystAgent
        from agents.momentum_tracker import MomentumTrackerAgent

        assert issubclass(MomentumTrackerAgent, BaseAnalystAgent)

    def test_agent_name(self):
        """Agent name is momentum_tracker."""
        from agents.momentum_tracker import MomentumTrackerAgent

        with patch("agents.base_agent.Agent"):
            agent = MomentumTrackerAgent()
        assert agent.name == "momentum_tracker"

    def test_agent_output_schema(self):
        """Output schema is MomentumReport."""
        from agents.momentum_tracker import MomentumTrackerAgent

        with patch("agents.base_agent.Agent"):
            agent = MomentumTrackerAgent()
        assert agent._output_schema is MomentumReport

    def test_agent_tools_include_technical_analysis(self):
        """Tools list includes get_technical_analysis."""
        from agents.momentum_tracker import MomentumTrackerAgent, get_technical_analysis

        with patch("agents.base_agent.Agent"):
            agent = MomentumTrackerAgent()
        tool_names = [fn.__name__ for fn in agent._tools]
        assert "get_technical_analysis" in tool_names

    def test_agent_card(self):
        """get_agent_card() returns valid dict."""
        from agents.momentum_tracker import MomentumTrackerAgent

        with patch("agents.base_agent.Agent"):
            agent = MomentumTrackerAgent()
        card = agent.get_agent_card()
        assert card["name"] == "momentum_tracker"
        assert "get_technical_analysis" in card["capabilities"]
        assert card["output_schema"] == "MomentumReport"

    def test_module_level_agent_instance(self):
        """Module-level momentum_tracker is a MomentumTrackerAgent."""
        with patch("agents.base_agent.Agent"):
            from agents import momentum_tracker as mt_module
            assert hasattr(mt_module, "momentum_tracker")
            from agents.momentum_tracker import MomentumTrackerAgent
            assert isinstance(mt_module.momentum_tracker, MomentumTrackerAgent)

    def test_factory_function(self):
        """create_momentum_tracker() returns a valid agent."""
        with patch("agents.base_agent.Agent"):
            from agents.momentum_tracker import create_momentum_tracker
            agent = create_momentum_tracker()
            assert agent.name == "momentum_tracker"

    @pytest.mark.asyncio
    async def test_analyze_success(self):
        """Mock LLM returns valid MomentumReport JSON."""
        from agents.momentum_tracker import MomentumTrackerAgent

        report_json = MomentumReport(
            ticker="AAPL",
            agent_name="momentum_tracker",
            signal="BUY",
            confidence=0.75,
            reasoning="Strong technical signals",
            rsi_14=45.0,
            macd_signal=0.5,
            above_sma_50=True,
            above_sma_200=True,
            volume_trend="increasing",
            price_momentum_score=0.6,
        ).model_dump_json()

        mock_part = MagicMock()
        mock_part.text = report_json

        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = MagicMock()
        mock_event.content.parts = [mock_part]

        async def mock_run_async(**kwargs):
            yield mock_event

        with patch("agents.base_agent.Agent"), \
             patch("agents.base_agent.InMemorySessionService") as mock_svc, \
             patch("agents.base_agent.Runner") as mock_runner_cls:
            mock_session = MagicMock()
            mock_session.id = "test-session"
            mock_svc.return_value.create_session = AsyncMock(return_value=mock_session)
            mock_runner_cls.return_value.run_async = mock_run_async

            agent = MomentumTrackerAgent()
            result = await agent.analyze("AAPL")

        assert isinstance(result, MomentumReport)
        assert result.ticker == "AAPL"
        assert result.signal == "BUY"
        assert result.rsi_14 == 45.0

    @pytest.mark.asyncio
    async def test_analyze_failure_fallback(self):
        """LLM failure produces HOLD/0.0 fallback."""
        from agents.momentum_tracker import MomentumTrackerAgent

        with patch("agents.base_agent.Agent"), \
             patch("agents.base_agent.InMemorySessionService") as mock_svc, \
             patch("agents.base_agent.Runner") as mock_runner_cls:
            mock_svc.return_value.create_session = AsyncMock(
                side_effect=Exception("LLM unavailable")
            )

            agent = MomentumTrackerAgent()
            result = await agent.analyze("AAPL")

        assert isinstance(result, AnalystReport)
        assert result.signal == "HOLD"
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()
