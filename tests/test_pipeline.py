"""Tests for S10.3 -- Integration Test: Full Pipeline.

End-to-end tests that exercise the FastAPI app with all agents mocked.
Verifies: single-ticker analysis, portfolio analysis, verdict storage,
session_id consistency, graceful degradation, and error handling.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)

# ---------------------------------------------------------------------------
# Fixtures: mock agent reports
# ---------------------------------------------------------------------------

VALID_SIGNALS = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}


def _make_valuation(ticker: str = "AAPL") -> ValuationReport:
    return ValuationReport(
        ticker=ticker,
        agent_name="ValuationScout",
        signal="BUY",
        confidence=0.8,
        reasoning="Strong fundamentals",
        pe_ratio=25.0,
        pb_ratio=6.0,
        revenue_growth=0.12,
        debt_to_equity=1.5,
        fcf_yield=0.04,
        intrinsic_value_gap=0.15,
    )


def _make_momentum(ticker: str = "AAPL") -> MomentumReport:
    return MomentumReport(
        ticker=ticker,
        agent_name="MomentumTracker",
        signal="BUY",
        confidence=0.75,
        reasoning="Bullish technicals",
        rsi_14=55.0,
        macd_signal=0.5,
        above_sma_50=True,
        above_sma_200=True,
        volume_trend="increasing",
        price_momentum_score=0.6,
    )


def _make_pulse(ticker: str = "AAPL") -> PulseReport:
    return PulseReport(
        ticker=ticker,
        agent_name="PulseMonitor",
        signal="BUY",
        confidence=0.65,
        reasoning="Positive sentiment",
        sentiment_score=0.6,
        article_count=5,
        top_headlines=["Good news"],
        event_flags=[],
    )


def _make_economy(ticker: str = "AAPL") -> EconomyReport:
    return EconomyReport(
        ticker=ticker,
        agent_name="EconomyWatcher",
        signal="HOLD",
        confidence=0.7,
        reasoning="Stable macro",
        gdp_growth=2.5,
        inflation_rate=3.0,
        fed_funds_rate=5.25,
        unemployment_rate=3.8,
        macro_regime="expansion",
    )


def _make_compliance(ticker: str = "AAPL") -> ComplianceReport:
    return ComplianceReport(
        ticker=ticker,
        agent_name="ComplianceChecker",
        signal="HOLD",
        confidence=0.9,
        reasoning="Clean filings",
        latest_filing_type="10-K",
        days_since_filing=30,
        risk_flags=[],
        risk_score=0.1,
    )


def _make_risk(ticker: str = "AAPL") -> RiskGuardianReport:
    return RiskGuardianReport(
        ticker=ticker,
        agent_name="RiskGuardian",
        signal="HOLD",
        confidence=0.8,
        reasoning="Moderate risk",
        beta=1.1,
        annualized_volatility=0.25,
        sharpe_ratio=1.5,
        max_drawdown=-0.15,
        suggested_position_size=0.05,
        var_95=-0.03,
    )


def _build_mock_agents(ticker: str = "AAPL") -> list[MagicMock]:
    """Build a list of 6 mock agents (5 directional + RiskGuardian)."""
    agent_configs = [
        ("valuation_scout", _make_valuation),
        ("momentum_tracker", _make_momentum),
        ("pulse_monitor", _make_pulse),
        ("economy_watcher", _make_economy),
        ("compliance_checker", _make_compliance),
        ("risk_guardian", _make_risk),
    ]
    agents = []
    for name, factory in agent_configs:
        agent = MagicMock()
        agent.name = name
        agent.analyze = AsyncMock(return_value=factory(ticker))
        agent.get_agent_card = MagicMock(return_value={"name": name})
        agents.append(agent)
    return agents


# ---------------------------------------------------------------------------
# App fixture with mocked agents
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_agents():
    """Return a list of 6 mock agents."""
    return _build_mock_agents()


@pytest.fixture
def app_with_mocked_agents(mock_agents):
    """Create the real FastAPI app but patch MarketConductor._lazy_load_agents."""
    with patch(
        "agents.market_conductor.MarketConductor._lazy_load_agents",
        return_value=mock_agents,
    ):
        from app import create_app

        test_app = create_app()
        yield test_app, mock_agents


@pytest.fixture
def client(app_with_mocked_agents):
    """Synchronous TestClient for the app with mocked agents."""
    test_app, _ = app_with_mocked_agents
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_and_agents(app_with_mocked_agents):
    """Return both client and mock agents for assertion on call counts."""
    test_app, agents = app_with_mocked_agents
    with TestClient(test_app, raise_server_exceptions=False) as c:
        yield c, agents


# ---------------------------------------------------------------------------
# FR-1: Single Ticker Integration Test
# ---------------------------------------------------------------------------


class TestSingleTickerAnalysis:
    """POST /api/v1/analyze/AAPL returns a valid FinalVerdict."""

    def test_analyze_single_ticker_returns_valid_verdict(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ticker"] == "AAPL"
        assert data["final_signal"] in VALID_SIGNALS
        assert 0.0 <= data["overall_confidence"] <= 1.0
        assert data["session_id"] != ""
        # Verify session_id is a valid UUID
        uuid.UUID(data["session_id"])

    def test_analyze_response_has_analyst_signals(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        # analyst_signals should contain entries from directional agents
        assert isinstance(data["analyst_signals"], dict)
        assert len(data["analyst_signals"]) >= 1


# ---------------------------------------------------------------------------
# FR-2: All Agents Called
# ---------------------------------------------------------------------------


class TestAllAgentsCalled:
    """Verify all 6 agents are invoked during a single-ticker analysis."""

    def test_all_agents_called_during_analysis(self, client_and_agents):
        client, agents = client_and_agents
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200

        for agent in agents:
            agent.analyze.assert_called_once()
            call_args = agent.analyze.call_args
            assert call_args[0][0] == "AAPL"


# ---------------------------------------------------------------------------
# FR-3: Verdict Stored in InsightVault
# ---------------------------------------------------------------------------


class TestVerdictStorage:
    """Verify verdict is stored and retrievable by session_id."""

    def test_verdict_stored_in_vault(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        # Retrieve the verdict by session_id
        get_resp = client.get(f"/api/v1/verdict/{session_id}")
        assert get_resp.status_code == 200
        stored = get_resp.json()
        assert stored["session_id"] == session_id
        assert stored["ticker"] == "AAPL"

    def test_nonexistent_session_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/verdict/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FR-5: Session ID Consistency
# ---------------------------------------------------------------------------


class TestSessionIdConsistency:
    """Session ID is consistent from API response through to stored verdict."""

    def test_session_id_consistency(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        session_id = data["session_id"]

        # Retrieve and compare
        get_resp = client.get(f"/api/v1/verdict/{session_id}")
        assert get_resp.status_code == 200
        stored = get_resp.json()
        assert stored["session_id"] == session_id
        assert stored["ticker"] == data["ticker"]
        assert stored["final_signal"] == data["final_signal"]


# ---------------------------------------------------------------------------
# FR-4: Portfolio Integration Test
# ---------------------------------------------------------------------------


class TestPortfolioAnalysis:
    """POST /api/v1/portfolio returns valid PortfolioInsight."""

    @pytest.fixture
    def portfolio_client(self):
        """Client with agents that handle multiple tickers."""
        def _make_agents_for_any_ticker(self_ref=None):
            """Return agents whose analyze() builds reports from the given ticker."""
            agent_configs = [
                ("valuation_scout", _make_valuation),
                ("momentum_tracker", _make_momentum),
                ("pulse_monitor", _make_pulse),
                ("economy_watcher", _make_economy),
                ("compliance_checker", _make_compliance),
                ("risk_guardian", _make_risk),
            ]
            agents = []
            for name, factory in agent_configs:
                agent = MagicMock()
                agent.name = name
                # side_effect: use the first positional arg as ticker
                agent.analyze = AsyncMock(side_effect=lambda t, f=factory: f(t))
                agent.get_agent_card = MagicMock(return_value={"name": name})
                agents.append(agent)
            return agents

        mock_agents = _make_agents_for_any_ticker()
        with patch(
            "agents.market_conductor.MarketConductor._lazy_load_agents",
            return_value=mock_agents,
        ):
            from app import create_app

            test_app = create_app()
            with TestClient(test_app, raise_server_exceptions=False) as c:
                yield c, mock_agents

    def test_portfolio_analysis_returns_valid_insight(self, portfolio_client):
        client, _ = portfolio_client
        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "MSFT", "GOOGL"]})
        assert resp.status_code == 200
        data = resp.json()

        assert set(data["tickers"]) == {"AAPL", "MSFT", "GOOGL"}
        assert len(data["verdicts"]) == 3
        assert data["portfolio_signal"] in VALID_SIGNALS
        assert 0.0 <= data["diversification_score"] <= 1.0

    def test_portfolio_all_tickers_analyzed(self, portfolio_client):
        client, agents = portfolio_client
        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "MSFT"]})
        assert resp.status_code == 200
        data = resp.json()

        # Each ticker should appear in the verdicts
        verdict_tickers = {v["ticker"] for v in data["verdicts"]}
        assert verdict_tickers == {"AAPL", "MSFT"}

    def test_portfolio_each_verdict_is_valid(self, portfolio_client):
        client, _ = portfolio_client
        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "TSLA"]})
        assert resp.status_code == 200
        data = resp.json()

        for verdict in data["verdicts"]:
            assert verdict["final_signal"] in VALID_SIGNALS
            assert 0.0 <= verdict["overall_confidence"] <= 1.0
            assert verdict["session_id"] != ""


# ---------------------------------------------------------------------------
# FR-6: Graceful Degradation in Integration
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """When agents fail, the pipeline still returns a valid verdict."""

    @pytest.fixture
    def degraded_client(self):
        """Client where ValuationScout raises an exception."""
        agents = _build_mock_agents()
        # Make ValuationScout fail
        agents[0].analyze = AsyncMock(side_effect=RuntimeError("Polygon API down"))

        with patch(
            "agents.market_conductor.MarketConductor._lazy_load_agents",
            return_value=agents,
        ):
            from app import create_app

            test_app = create_app()
            with TestClient(test_app, raise_server_exceptions=False) as c:
                yield c

    def test_graceful_degradation_single_agent_failure(self, degraded_client):
        resp = degraded_client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ticker"] == "AAPL"
        assert data["final_signal"] in VALID_SIGNALS
        assert 0.0 <= data["overall_confidence"] <= 1.0

    def test_graceful_degradation_warning_in_key_drivers(self, degraded_client):
        resp = degraded_client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        # key_drivers should contain a WARNING about the failed agent
        warnings = [d for d in data["key_drivers"] if "WARNING" in d]
        assert len(warnings) >= 1
        assert any("valuation_scout" in w for w in warnings)


# ---------------------------------------------------------------------------
# FR-7: Error Handling Integration
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Invalid requests return proper error responses."""

    def test_invalid_ticker_returns_error(self, client):
        resp = client.post("/api/v1/analyze/TOOLONGTICKERSYMBOLNAME123")
        assert resp.status_code == 400
        data = resp.json()
        assert data["error"]["code"] == "INVALID_TICKER"

    def test_empty_portfolio_returns_error(self, client):
        resp = client.post("/api/v1/portfolio", json={"tickers": []})
        assert resp.status_code == 422

    def test_missing_portfolio_body_returns_error(self, client):
        resp = client.post("/api/v1/portfolio")
        assert resp.status_code == 422
