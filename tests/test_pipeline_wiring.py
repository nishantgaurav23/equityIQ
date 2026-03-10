"""Tests for S10.1 -- Pipeline Wiring (session_id threading)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PortfolioInsight,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)
from models.signal_fusion import SignalFusionModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _all_reports(ticker: str = "AAPL") -> list:
    return [
        _make_valuation(ticker),
        _make_momentum(ticker),
        _make_pulse(ticker),
        _make_economy(ticker),
        _make_compliance(ticker),
    ]


# ---------------------------------------------------------------------------
# FR-4: SignalFusionModel.predict() session_id threading
# ---------------------------------------------------------------------------


class TestSignalFusionSessionId:
    """SignalFusionModel.predict() should accept and use a provided session_id."""

    def test_predict_uses_provided_session_id(self):
        model = SignalFusionModel()
        sid = str(uuid.uuid4())
        verdict = model.predict(_all_reports(), session_id=sid)
        assert verdict.session_id == sid

    def test_predict_generates_uuid_when_none(self):
        model = SignalFusionModel()
        verdict = model.predict(_all_reports(), session_id=None)
        assert verdict.session_id != ""
        # Verify it's a valid UUID
        uuid.UUID(verdict.session_id)

    def test_predict_generates_uuid_by_default(self):
        model = SignalFusionModel()
        verdict = model.predict(_all_reports())
        assert verdict.session_id != ""
        uuid.UUID(verdict.session_id)

    def test_predict_empty_reports_uses_session_id(self):
        model = SignalFusionModel()
        sid = str(uuid.uuid4())
        verdict = model.predict([], session_id=sid)
        assert verdict.session_id == sid

    def test_predict_empty_reports_no_session_id(self):
        model = SignalFusionModel()
        verdict = model.predict([])
        assert verdict.session_id != ""
        uuid.UUID(verdict.session_id)


# ---------------------------------------------------------------------------
# FR-3: SignalSynthesizer.synthesize() session_id threading
# ---------------------------------------------------------------------------


class TestSynthesizerSessionId:
    """SignalSynthesizer.synthesize() should thread session_id to predict()."""

    @pytest.mark.asyncio
    async def test_synthesize_threads_session_id(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        sid = str(uuid.uuid4())
        reports = _all_reports()
        verdict = await synth.synthesize(reports, session_id=sid)
        assert verdict.session_id == sid

    @pytest.mark.asyncio
    async def test_synthesize_without_session_id(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_reports()
        verdict = await synth.synthesize(reports)
        assert verdict.session_id != ""
        uuid.UUID(verdict.session_id)

    @pytest.mark.asyncio
    async def test_synthesize_with_risk_report_threads_session_id(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        sid = str(uuid.uuid4())
        reports = _all_reports()
        risk = _make_risk()
        verdict = await synth.synthesize(reports, risk_report=risk, session_id=sid)
        assert verdict.session_id == sid
        assert verdict.risk_summary != ""

    @pytest.mark.asyncio
    async def test_synthesize_empty_reports_uses_session_id(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        sid = str(uuid.uuid4())
        verdict = await synth.synthesize([], session_id=sid)
        assert verdict.session_id == sid


# ---------------------------------------------------------------------------
# FR-2: MarketConductor.analyze() session_id threading
# ---------------------------------------------------------------------------


class TestConductorSessionId:
    """MarketConductor.analyze() should accept and thread session_id."""

    @pytest.mark.asyncio
    async def test_analyze_threads_session_id(self):
        from agents.market_conductor import MarketConductor

        conductor = MarketConductor(vault=None, timeout=5.0)
        sid = str(uuid.uuid4())

        # Mock agents
        mock_agent = MagicMock()
        mock_agent.name = "valuation_scout"
        mock_agent.analyze = AsyncMock(return_value=_make_valuation())
        conductor._agents = [mock_agent]

        # Mock synthesizer
        expected_verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.8,
            session_id=sid,
        )
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(return_value=expected_verdict)
        conductor._synthesizer = mock_synth

        verdict = await conductor.analyze("AAPL", session_id=sid)
        assert verdict.session_id == sid

        # Verify session_id was passed to synthesizer
        mock_synth.synthesize.assert_called_once()
        call_kwargs = mock_synth.synthesize.call_args
        assert call_kwargs.kwargs.get("session_id") == sid

    @pytest.mark.asyncio
    async def test_analyze_generates_session_id_when_none(self):
        from agents.market_conductor import MarketConductor

        conductor = MarketConductor(vault=None, timeout=5.0)

        mock_agent = MagicMock()
        mock_agent.name = "valuation_scout"
        mock_agent.analyze = AsyncMock(return_value=_make_valuation())
        conductor._agents = [mock_agent]

        # Use real synthesizer to check session_id generation
        verdict = await conductor.analyze("AAPL")
        assert verdict.session_id != ""
        uuid.UUID(verdict.session_id)

    @pytest.mark.asyncio
    async def test_analyze_stores_verdict_with_session_id(self):
        from agents.market_conductor import MarketConductor

        mock_vault = MagicMock()
        mock_vault.store_verdict = AsyncMock()
        conductor = MarketConductor(vault=mock_vault, timeout=5.0)
        sid = str(uuid.uuid4())

        mock_agent = MagicMock()
        mock_agent.name = "valuation_scout"
        mock_agent.analyze = AsyncMock(return_value=_make_valuation())
        conductor._agents = [mock_agent]

        verdict = await conductor.analyze("AAPL", session_id=sid)
        assert verdict.session_id == sid

        # Verify vault received the verdict with correct session_id
        mock_vault.store_verdict.assert_called_once()
        stored = mock_vault.store_verdict.call_args[0][0]
        assert stored.session_id == sid

    @pytest.mark.asyncio
    async def test_analyze_no_agents_uses_session_id(self):
        from agents.market_conductor import MarketConductor

        conductor = MarketConductor(vault=None, timeout=5.0)
        conductor._agents = []
        sid = str(uuid.uuid4())
        verdict = await conductor.analyze("AAPL", session_id=sid)
        assert verdict.session_id == sid
        assert verdict.final_signal == "HOLD"


# ---------------------------------------------------------------------------
# FR-1: API routes session_id generation
# ---------------------------------------------------------------------------


class TestAPISessionId:
    """API routes should generate session_id and pass to conductor."""

    @pytest.fixture
    def app(self):
        from fastapi import FastAPI

        from api.routes import router

        test_app = FastAPI()
        test_app.include_router(router)
        test_app.state.conductor = MagicMock()
        test_app.state.vault = MagicMock()
        test_app.state.history_retriever = MagicMock()
        return test_app

    @pytest.fixture
    def client(self, app):
        from fastapi.testclient import TestClient

        return TestClient(app, raise_server_exceptions=False)

    def test_analyze_passes_session_id_to_conductor(self, client, app):
        verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.8,
            session_id="test-session-123",
        )
        app.state.conductor.analyze = AsyncMock(return_value=verdict)

        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200

        # Verify conductor.analyze was called with a session_id kwarg
        app.state.conductor.analyze.assert_called_once()
        call_kwargs = app.state.conductor.analyze.call_args
        assert "session_id" in call_kwargs.kwargs
        sid = call_kwargs.kwargs["session_id"]
        # Must be a valid UUID
        uuid.UUID(sid)

    def test_analyze_response_includes_session_id(self, client, app):
        sid = str(uuid.uuid4())
        verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.8,
            session_id=sid,
        )
        app.state.conductor.analyze = AsyncMock(return_value=verdict)

        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid

    def test_portfolio_passes_session_id(self, client, app):
        insight = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[],
            portfolio_signal="HOLD",
            diversification_score=0.0,
            top_pick=None,
        )
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=insight)

        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL"]})
        assert resp.status_code == 200

        # Verify session_id was passed
        app.state.conductor.analyze_portfolio.assert_called_once()
        call_kwargs = app.state.conductor.analyze_portfolio.call_args
        assert "session_id" in call_kwargs.kwargs
        uuid.UUID(call_kwargs.kwargs["session_id"])


# ---------------------------------------------------------------------------
# FR-5: End-to-end session_id consistency
# ---------------------------------------------------------------------------


class TestEndToEndSessionConsistency:
    """Session ID should be consistent from API entry through to stored verdict."""

    @pytest.mark.asyncio
    async def test_session_id_consistent_through_pipeline(self):
        """Verify session_id flows: conductor -> synthesizer -> fusion -> verdict."""
        from agents.market_conductor import MarketConductor

        mock_vault = MagicMock()
        mock_vault.store_verdict = AsyncMock()
        conductor = MarketConductor(vault=mock_vault, timeout=5.0)

        sid = str(uuid.uuid4())

        # Set up agents that return real reports
        agents = []
        for report in _all_reports():
            agent = MagicMock()
            agent.name = report.agent_name.lower().replace(" ", "_")
            agent.analyze = AsyncMock(return_value=report)
            agents.append(agent)

        risk = _make_risk()
        risk_agent = MagicMock()
        risk_agent.name = "risk_guardian"
        risk_agent.analyze = AsyncMock(return_value=risk)
        agents.append(risk_agent)

        conductor._agents = agents

        verdict = await conductor.analyze("AAPL", session_id=sid)

        # Session ID should be consistent everywhere
        assert verdict.session_id == sid
        assert verdict.ticker == "AAPL"

        # Vault should have stored the same session_id
        mock_vault.store_verdict.assert_called_once()
        stored_verdict = mock_vault.store_verdict.call_args[0][0]
        assert stored_verdict.session_id == sid

    @pytest.mark.asyncio
    async def test_backward_compat_no_session_id(self):
        """Calling analyze() without session_id should still work and auto-generate one."""
        from agents.market_conductor import MarketConductor

        conductor = MarketConductor(vault=None, timeout=5.0)

        agents = []
        for report in _all_reports():
            agent = MagicMock()
            agent.name = report.agent_name.lower().replace(" ", "_")
            agent.analyze = AsyncMock(return_value=report)
            agents.append(agent)

        conductor._agents = agents

        verdict = await conductor.analyze("AAPL")
        assert verdict.session_id != ""
        uuid.UUID(verdict.session_id)
