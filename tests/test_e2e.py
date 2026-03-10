"""Tests for S14.4 -- End-to-End Smoke Test.

Full smoke tests exercising the complete EquityIQ analysis pipeline for AAPL
with all external APIs mocked. Validates FinalVerdict completeness, timing,
agent signals, vault storage, compliance override, and portfolio analysis.
"""

from __future__ import annotations

import time
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

VALID_SIGNALS = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}

DIRECTIONAL_AGENT_NAMES = {
    "valuation_scout",
    "momentum_tracker",
    "pulse_monitor",
    "economy_watcher",
    "compliance_checker",
}

# ---------------------------------------------------------------------------
# Mock report factories
# ---------------------------------------------------------------------------


def _make_valuation(ticker: str = "AAPL") -> ValuationReport:
    return ValuationReport(
        ticker=ticker,
        agent_name="valuation_scout",
        signal="BUY",
        confidence=0.8,
        reasoning="Strong fundamentals with solid revenue growth",
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
        agent_name="momentum_tracker",
        signal="BUY",
        confidence=0.75,
        reasoning="Bullish technicals with upward momentum",
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
        agent_name="pulse_monitor",
        signal="BUY",
        confidence=0.65,
        reasoning="Positive sentiment across multiple sources",
        sentiment_score=0.6,
        article_count=5,
        top_headlines=["Apple reports record revenue", "New product launch successful"],
        event_flags=[],
    )


def _make_economy(ticker: str = "AAPL") -> EconomyReport:
    return EconomyReport(
        ticker=ticker,
        agent_name="economy_watcher",
        signal="HOLD",
        confidence=0.7,
        reasoning="Stable macro environment",
        gdp_growth=2.5,
        inflation_rate=3.0,
        fed_funds_rate=5.25,
        unemployment_rate=3.8,
        macro_regime="expansion",
    )


def _make_compliance(ticker: str = "AAPL", risk_flags: list[str] | None = None) -> ComplianceReport:
    return ComplianceReport(
        ticker=ticker,
        agent_name="compliance_checker",
        signal="HOLD",
        confidence=0.9,
        reasoning="Clean filings, no regulatory concerns",
        latest_filing_type="10-K",
        days_since_filing=30,
        risk_flags=risk_flags or [],
        risk_score=0.1,
    )


def _make_risk(ticker: str = "AAPL") -> RiskGuardianReport:
    return RiskGuardianReport(
        ticker=ticker,
        agent_name="risk_guardian",
        signal="HOLD",
        confidence=0.8,
        reasoning="Moderate risk profile",
        beta=1.1,
        annualized_volatility=0.25,
        sharpe_ratio=1.5,
        max_drawdown=-0.15,
        suggested_position_size=0.05,
        var_95=-0.03,
    )


def _build_mock_agents(ticker: str = "AAPL") -> list[MagicMock]:
    """Build 6 mock agents (5 directional + RiskGuardian)."""
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


def _build_dynamic_mock_agents() -> list[MagicMock]:
    """Build mock agents that respond to any ticker dynamically."""
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
        agent.analyze = AsyncMock(side_effect=lambda t, f=factory: f(t))
        agent.get_agent_card = MagicMock(return_value={"name": name})
        agents.append(agent)
    return agents


def _build_compliance_override_agents(risk_flags: list[str]) -> list[MagicMock]:
    """Build mock agents where ComplianceChecker has specified risk_flags."""
    agent_configs = [
        ("valuation_scout", lambda t: _make_valuation(t)),
        ("momentum_tracker", lambda t: _make_momentum(t)),
        ("pulse_monitor", lambda t: _make_pulse(t)),
        ("economy_watcher", lambda t: _make_economy(t)),
        (
            "compliance_checker",
            lambda t: _make_compliance(t, risk_flags=risk_flags),
        ),
        ("risk_guardian", lambda t: _make_risk(t)),
    ]
    agents = []
    for name, factory in agent_configs:
        agent = MagicMock()
        agent.name = name
        agent.analyze = AsyncMock(side_effect=factory)
        agent.get_agent_card = MagicMock(return_value={"name": name})
        agents.append(agent)
    return agents


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """TestClient with all agents mocked (AAPL fixed responses)."""
    mock_agents = _build_mock_agents("AAPL")
    with patch(
        "agents.market_conductor.MarketConductor._lazy_load_agents",
        return_value=mock_agents,
    ):
        from app import create_app

        test_app = create_app()
        with TestClient(test_app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def dynamic_client():
    """TestClient with agents that respond dynamically to any ticker."""
    mock_agents = _build_dynamic_mock_agents()
    with patch(
        "agents.market_conductor.MarketConductor._lazy_load_agents",
        return_value=mock_agents,
    ):
        from app import create_app

        test_app = create_app()
        with TestClient(test_app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def compliance_override_client():
    """TestClient with ComplianceChecker flagging going_concern."""
    mock_agents = _build_compliance_override_agents(["going_concern"])
    with patch(
        "agents.market_conductor.MarketConductor._lazy_load_agents",
        return_value=mock_agents,
    ):
        from app import create_app

        test_app = create_app()
        with TestClient(test_app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# FR-1: Full AAPL Analysis Smoke Test
# ---------------------------------------------------------------------------


class TestFullAAPLAnalysis:
    """POST /api/v1/analyze/AAPL returns a complete FinalVerdict."""

    def test_full_aapl_analysis_returns_verdict(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        assert data["ticker"] == "AAPL"
        assert data["final_signal"] in VALID_SIGNALS
        assert isinstance(data["overall_confidence"], float)
        assert isinstance(data["key_drivers"], list)
        assert isinstance(data["analyst_signals"], dict)
        assert isinstance(data["analyst_details"], dict)
        assert data["session_id"] != ""
        assert "timestamp" in data

    def test_verdict_has_risk_summary(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_summary" in data
        assert "risk_level" in data
        assert data["risk_level"] in ("LOW", "MEDIUM", "HIGH")


# ---------------------------------------------------------------------------
# FR-2: Response Time Under 30 Seconds
# ---------------------------------------------------------------------------


class TestResponseTime:
    """Verify the analysis completes within 30 seconds."""

    def test_response_time_under_30s(self, client):
        start = time.monotonic()
        resp = client.post("/api/v1/analyze/AAPL")
        elapsed = time.monotonic() - start

        assert resp.status_code == 200
        assert elapsed < 30.0, f"Analysis took {elapsed:.2f}s, exceeds 30s limit"

    def test_execution_time_ms_populated(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)
        assert data["execution_time_ms"] >= 0


# ---------------------------------------------------------------------------
# FR-3: All Agent Signals Present
# ---------------------------------------------------------------------------


class TestAllAgentSignalsPresent:
    """Verify all 5 directional agents are represented in analyst_signals."""

    def test_all_agent_signals_present(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        signals = data["analyst_signals"]
        assert isinstance(signals, dict)
        assert len(signals) >= 5, f"Expected 5+ agent signals, got {len(signals)}"

        for signal_value in signals.values():
            assert signal_value in {"BUY", "HOLD", "SELL"}


# ---------------------------------------------------------------------------
# FR-4: Verdict Stored in Memory
# ---------------------------------------------------------------------------


class TestVerdictStorage:
    """Verify the verdict is stored and retrievable via /verdict/{session_id}."""

    def test_verdict_stored_in_vault(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]

        get_resp = client.get(f"/api/v1/verdict/{session_id}")
        assert get_resp.status_code == 200
        stored = get_resp.json()
        assert stored["session_id"] == session_id
        assert stored["ticker"] == "AAPL"

    def test_nonexistent_session_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/verdict/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# FR-5: Health Endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """GET /health returns status OK."""

    def test_health_endpoint_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "environment" in data
        assert "version" in data


# ---------------------------------------------------------------------------
# FR-6: Agent Details Populated
# ---------------------------------------------------------------------------


class TestAgentDetailsPopulated:
    """Verify analyst_details has structured AgentDetail entries."""

    def test_agent_details_populated(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        details = data["analyst_details"]
        assert isinstance(details, dict)
        assert len(details) >= 5, f"Expected 5+ agent details, got {len(details)}"

        for agent_name, detail in details.items():
            assert "agent_name" in detail
            assert "signal" in detail
            assert "confidence" in detail
            assert "reasoning" in detail
            assert 0.0 <= detail["confidence"] <= 1.0
            assert detail["signal"] in {"BUY", "HOLD", "SELL"}

    def test_agent_details_have_key_metrics(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        details = data["analyst_details"]
        # At least some agents should have non-empty key_metrics
        agents_with_metrics = [name for name, d in details.items() if d.get("key_metrics")]
        assert len(agents_with_metrics) >= 3, "Expected at least 3 agents with key_metrics"


# ---------------------------------------------------------------------------
# FR-7: Compliance Override Smoke Test
# ---------------------------------------------------------------------------


class TestComplianceOverride:
    """When ComplianceChecker flags going_concern, final signal is forced to SELL."""

    def test_compliance_going_concern_forces_sell(self, compliance_override_client):
        resp = compliance_override_client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()

        assert data["final_signal"] in (
            "SELL",
            "STRONG_SELL",
        ), f"Expected SELL/STRONG_SELL with going_concern, got {data['final_signal']}"

        # key_drivers should mention the compliance override
        drivers = data.get("key_drivers", [])
        assert any("going_concern" in d.lower() or "compliance" in d.lower() for d in drivers), (
            f"Expected going_concern in key_drivers, got {drivers}"
        )


# ---------------------------------------------------------------------------
# FR-8: Portfolio Smoke Test
# ---------------------------------------------------------------------------


class TestPortfolioSmoke:
    """POST /api/v1/portfolio with multiple tickers returns PortfolioInsight."""

    def test_portfolio_smoke(self, dynamic_client):
        resp = dynamic_client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "GOOGL"]})
        assert resp.status_code == 200
        data = resp.json()

        assert set(data["tickers"]) == {"AAPL", "GOOGL"}
        assert len(data["verdicts"]) == 2
        assert data["portfolio_signal"] in VALID_SIGNALS
        assert 0.0 <= data["diversification_score"] <= 1.0

    def test_portfolio_each_verdict_valid(self, dynamic_client):
        resp = dynamic_client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "MSFT"]})
        assert resp.status_code == 200
        data = resp.json()

        for verdict in data["verdicts"]:
            assert verdict["ticker"] in {"AAPL", "MSFT"}
            assert verdict["final_signal"] in VALID_SIGNALS
            assert 0.0 <= verdict["overall_confidence"] <= 1.0
            assert verdict["session_id"] != ""


# ---------------------------------------------------------------------------
# Additional: Confidence Range and Session ID Validation
# ---------------------------------------------------------------------------


class TestVerdictFieldValidation:
    """Cross-cutting validation on FinalVerdict fields."""

    def test_verdict_confidence_in_range(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert 0.0 <= data["overall_confidence"] <= 1.0

    def test_verdict_has_valid_session_id(self, client):
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        session_id = resp.json()["session_id"]
        # Should be a valid UUID
        parsed = uuid.UUID(session_id)
        assert str(parsed) == session_id
