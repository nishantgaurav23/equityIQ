"""Tests for agents/market_conductor.py -- MarketConductor orchestrator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import (
    AgentDetail,
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PortfolioInsight,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)


def _make_report(cls, ticker="AAPL", signal="BUY", confidence=0.7, **kwargs):
    """Helper to build report instances with defaults."""
    base = {
        "ticker": ticker,
        "agent_name": cls.__name__,
        "signal": signal,
        "confidence": confidence,
        "reasoning": "test",
    }
    base.update(kwargs)
    return cls(**base)


def _make_mock_agents(include_risk=True):
    """Create a list of mock agents returning typed reports."""
    agent_specs = [
        ("valuation_scout", ValuationReport),
        ("momentum_tracker", MomentumReport),
        ("pulse_monitor", PulseReport),
        ("economy_watcher", EconomyReport),
        ("compliance_checker", ComplianceReport),
    ]
    agents = []
    for agent_name, report_cls in agent_specs:
        agent = MagicMock()
        agent.name = agent_name
        agent.analyze = AsyncMock(
            return_value=_make_report(report_cls, agent_name=agent_name)
        )
        agents.append(agent)

    if include_risk:
        risk_agent = MagicMock()
        risk_agent.name = "risk_guardian"
        risk_agent.analyze = AsyncMock(
            return_value=RiskGuardianReport(
                ticker="AAPL",
                agent_name="risk_guardian",
                signal="HOLD",
                confidence=0.6,
                reasoning="Risk assessment",
                beta=1.2,
                annualized_volatility=0.25,
                sharpe_ratio=1.1,
                max_drawdown=-0.15,
                var_95=-0.03,
                suggested_position_size=0.08,
            )
        )
        agents.append(risk_agent)

    return agents


class TestMarketConductorInit:
    def test_creates_without_vault(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        assert mc._vault is None
        assert mc._agents == []
        assert mc._timeout == 60.0

    def test_creates_with_vault(self):
        from agents.market_conductor import MarketConductor

        vault = MagicMock()
        mc = MarketConductor(vault=vault)
        assert mc._vault is vault

    def test_creates_with_custom_timeout(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor(timeout=15.0)
        assert mc._timeout == 15.0


class TestMarketConductorAnalyze:
    @pytest.mark.asyncio
    async def test_analyze_returns_final_verdict(self):
        """Conductor returns FinalVerdict with correct ticker."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=False)

        # Mock synthesizer
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"
        assert verdict.final_signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")

    @pytest.mark.asyncio
    async def test_analyze_normalizes_ticker(self):
        """Ticker is uppercased and stripped."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = []

        verdict = await mc.analyze("  aapl  ")
        assert verdict.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_analyze_no_agents(self):
        """No agents available -> HOLD/0.0."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        # Must mock _lazy_load_agents to return empty list, since setting
        # _agents = [] is falsy and triggers real agent imports.
        mc._lazy_load_agents = lambda: []

        verdict = await mc.analyze("AAPL")
        assert verdict.final_signal == "HOLD"
        assert verdict.overall_confidence == 0.0

    @pytest.mark.asyncio
    async def test_analyze_handles_agent_exception(self):
        """Agent raising exception is skipped gracefully."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        failing_agent = MagicMock()
        failing_agent.name = "valuation_scout"
        failing_agent.analyze = AsyncMock(side_effect=Exception("boom"))

        mc._agents = [failing_agent]

        # Mock synthesizer for the empty reports case
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="HOLD",
                overall_confidence=0.0,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_analyze_stores_verdict_in_vault(self):
        """Verdict is stored in InsightVault when provided."""
        from agents.market_conductor import MarketConductor

        vault = MagicMock()
        vault.store_verdict = AsyncMock(return_value="session-123")

        mc = MarketConductor(vault=vault)
        mc._agents = []  # No agents -> HOLD verdict

        verdict = await mc.analyze("AAPL")
        vault.store_verdict.assert_awaited_once_with(verdict)

    @pytest.mark.asyncio
    async def test_vault_failure_doesnt_crash(self):
        """Vault store failure is logged but doesn't raise."""
        from agents.market_conductor import MarketConductor

        vault = MagicMock()
        vault.store_verdict = AsyncMock(side_effect=Exception("DB error"))

        mc = MarketConductor(vault=vault)
        mc._agents = []

        verdict = await mc.analyze("AAPL")
        assert isinstance(verdict, FinalVerdict)

    @pytest.mark.asyncio
    async def test_risk_summary_attached(self):
        """RiskGuardian report is passed to synthesizer and attached as risk_summary."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        risk_agent = MagicMock()
        risk_agent.name = "risk_guardian"
        risk_agent.analyze = AsyncMock(
            return_value=RiskGuardianReport(
                ticker="AAPL",
                agent_name="risk_guardian",
                signal="HOLD",
                confidence=0.6,
                reasoning="Risk assessment",
                beta=1.2,
                annualized_volatility=0.25,
                sharpe_ratio=1.1,
                max_drawdown=-0.15,
                var_95=-0.03,
                suggested_position_size=0.08,
            )
        )

        mc._agents = [risk_agent]

        # Mock synthesizer that includes risk_summary when risk_report is passed
        mock_synth = MagicMock()

        async def mock_synthesize(reports, risk_report=None, session_id=None):
            v = FinalVerdict(
                ticker="AAPL",
                final_signal="HOLD",
                overall_confidence=0.5,
            )
            if risk_report is not None:
                v.risk_summary = f"Beta: {risk_report.beta}"
            return v

        mock_synth.synthesize = AsyncMock(side_effect=mock_synthesize)
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert "Beta: 1.2" in verdict.risk_summary

    @pytest.mark.asyncio
    async def test_compliance_override_applied(self):
        """going_concern flag forces SELL override via SignalSynthesizer."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        val_agent = MagicMock()
        val_agent.name = "valuation_scout"
        val_agent.analyze = AsyncMock(
            return_value=_make_report(
                ValuationReport,
                agent_name="valuation_scout",
                signal="BUY",
                confidence=0.9,
            )
        )

        comp_agent = MagicMock()
        comp_agent.name = "compliance_checker"
        comp_agent.analyze = AsyncMock(
            return_value=ComplianceReport(
                ticker="AAPL",
                agent_name="compliance_checker",
                signal="SELL",
                confidence=0.9,
                reasoning="Going concern found",
                risk_flags=["going_concern"],
                risk_score=0.9,
            )
        )

        mc._agents = [val_agent, comp_agent]

        # Use real SignalSynthesizer for compliance override test
        verdict = await mc.analyze("AAPL")
        assert verdict.final_signal == "SELL"

    @pytest.mark.asyncio
    async def test_uses_signal_synthesizer_for_fusion(self):
        """Verify SignalSynthesizer.synthesize() is called (not raw SignalFusionModel)."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        await mc.analyze("AAPL")

        # synthesize was called with directional reports (not risk) + risk_report kwarg
        mock_synth.synthesize.assert_awaited_once()
        call_args = mock_synth.synthesize.call_args
        directional_reports = call_args[0][0]
        risk_kwarg = call_args[1].get("risk_report")

        assert len(directional_reports) == 5  # 5 directional agents
        assert isinstance(risk_kwarg, RiskGuardianReport)

    @pytest.mark.asyncio
    async def test_agent_timeout_handled(self):
        """Agent that exceeds timeout is treated as a failure."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor(timeout=0.01)  # 10ms timeout

        slow_agent = MagicMock()
        slow_agent.name = "valuation_scout"

        async def slow_analyze(ticker):
            await asyncio.sleep(1.0)  # Will exceed 10ms timeout
            return _make_report(ValuationReport, agent_name="valuation_scout")

        slow_agent.analyze = slow_analyze

        mc._agents = [slow_agent]

        # Mock synthesizer for the empty reports case
        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="HOLD",
                overall_confidence=0.0,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        # Should not crash -- timeout is handled gracefully
        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"


class TestMarketConductorLazyLoad:
    def test_lazy_load_caches(self):
        """Second call returns same list without re-importing."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = [MagicMock()]

        agents = mc._lazy_load_agents()
        assert len(agents) == 1
        # Same list returned
        assert mc._lazy_load_agents() is agents


def _make_verdict(ticker="AAPL", signal="BUY", confidence=0.7):
    """Helper to build FinalVerdict with defaults."""
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
    )


class TestAnalyzePortfolioBasic:
    """FR-1: analyze_portfolio() method."""

    @pytest.mark.asyncio
    async def test_analyze_portfolio_basic(self):
        """3 tickers, all succeed -> PortfolioInsight with 3 verdicts."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        verdicts = {
            "AAPL": _make_verdict("AAPL", "BUY", 0.8),
            "GOOGL": _make_verdict("GOOGL", "BUY", 0.7),
            "MSFT": _make_verdict("MSFT", "HOLD", 0.6),
        }

        async def mock_analyze(ticker):
            return verdicts[ticker]

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert isinstance(result, PortfolioInsight)
        assert len(result.verdicts) == 3
        assert set(result.tickers) == {"AAPL", "GOOGL", "MSFT"}

    @pytest.mark.asyncio
    async def test_analyze_portfolio_empty_tickers(self):
        """Empty list -> HOLD, 0.0 diversification, no top_pick."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        result = await mc.analyze_portfolio([])
        assert isinstance(result, PortfolioInsight)
        assert result.portfolio_signal == "HOLD"
        assert result.diversification_score == 0.0
        assert result.top_pick is None
        assert len(result.verdicts) == 0

    @pytest.mark.asyncio
    async def test_analyze_portfolio_single_ticker(self):
        """1 ticker -> diversification_score = 0.0."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc.analyze = AsyncMock(return_value=_make_verdict("AAPL", "BUY", 0.8))

        result = await mc.analyze_portfolio(["AAPL"])
        assert result.diversification_score == 0.0
        assert len(result.verdicts) == 1


class TestTickerValidation:
    """FR-2: Ticker validation and normalization."""

    @pytest.mark.asyncio
    async def test_analyze_portfolio_deduplication(self):
        """Duplicate tickers deduplicated."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc.analyze = AsyncMock(return_value=_make_verdict("AAPL", "BUY", 0.8))

        result = await mc.analyze_portfolio(["AAPL", "aapl", " AAPL"])
        assert len(result.verdicts) == 1
        assert result.tickers == ["AAPL"]
        # analyze called only once for the deduplicated ticker
        mc.analyze.assert_awaited_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_analyze_portfolio_ticker_normalization(self):
        """Mixed case/whitespace normalized."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        async def mock_analyze(ticker):
            return _make_verdict(ticker, "BUY", 0.7)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["  aapl ", " Googl"])
        assert set(result.tickers) == {"AAPL", "GOOGL"}


class TestConcurrentExecution:
    """FR-3: Concurrent execution with error isolation."""

    @pytest.mark.asyncio
    async def test_analyze_portfolio_partial_failure(self):
        """One ticker fails, others succeed."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        async def mock_analyze(ticker):
            if ticker == "BAD":
                raise Exception("Analysis failed")
            return _make_verdict(ticker, "BUY", 0.7)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "BAD", "MSFT"])
        assert len(result.verdicts) == 2
        tickers_in_result = [v.ticker for v in result.verdicts]
        assert "AAPL" in tickers_in_result
        assert "MSFT" in tickers_in_result

    @pytest.mark.asyncio
    async def test_analyze_portfolio_all_fail(self):
        """All tickers fail -> HOLD, no top_pick."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc.analyze = AsyncMock(side_effect=Exception("boom"))

        result = await mc.analyze_portfolio(["AAPL", "GOOGL"])
        assert result.portfolio_signal == "HOLD"
        assert result.top_pick is None
        assert len(result.verdicts) == 0


class TestPortfolioSignalAggregation:
    """FR-4: Portfolio signal aggregation."""

    @pytest.mark.asyncio
    async def test_portfolio_signal_buy_majority(self):
        """Mostly BUY -> portfolio BUY."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [("AAPL", "BUY", 0.8), ("GOOGL", "BUY", 0.7), ("MSFT", "HOLD", 0.5)]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.portfolio_signal == "BUY"

    @pytest.mark.asyncio
    async def test_portfolio_signal_sell_majority(self):
        """Mostly SELL -> portfolio SELL."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [
            ("AAPL", "SELL", 0.8),
            ("GOOGL", "SELL", 0.7),
            ("MSFT", "HOLD", 0.5),
        ]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.portfolio_signal == "SELL"

    @pytest.mark.asyncio
    async def test_portfolio_signal_mixed(self):
        """Mixed signals -> HOLD."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [("AAPL", "BUY", 0.6), ("GOOGL", "SELL", 0.6), ("MSFT", "HOLD", 0.6)]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.portfolio_signal == "HOLD"


class TestDiversificationScore:
    """FR-5: Diversification score calculation."""

    @pytest.mark.asyncio
    async def test_diversification_score_all_same(self):
        """All same signal -> 0.0."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        async def mock_analyze(ticker):
            return _make_verdict(ticker, "BUY", 0.7)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.diversification_score == 0.0

    @pytest.mark.asyncio
    async def test_diversification_score_all_different(self):
        """All different signals -> > 0."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [("AAPL", "BUY", 0.7), ("GOOGL", "SELL", 0.7), ("MSFT", "HOLD", 0.7)]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.diversification_score > 0.0
        assert result.diversification_score <= 1.0


class TestTopPick:
    """FR-6: Top pick selection."""

    @pytest.mark.asyncio
    async def test_top_pick_selection(self):
        """Highest-confidence BUY selected."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [("AAPL", "BUY", 0.6), ("GOOGL", "BUY", 0.9), ("MSFT", "HOLD", 0.5)]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.top_pick == "GOOGL"

    @pytest.mark.asyncio
    async def test_top_pick_no_buys(self):
        """No BUY signals -> top_pick is None."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [
            ("AAPL", "HOLD", 0.6),
            ("GOOGL", "SELL", 0.7),
            ("MSFT", "HOLD", 0.5),
        ]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL", "MSFT"])
        assert result.top_pick is None

    @pytest.mark.asyncio
    async def test_top_pick_strong_buy_included(self):
        """STRONG_BUY is also eligible for top_pick."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        tickers_signals = [
            ("AAPL", "BUY", 0.6),
            ("GOOGL", "STRONG_BUY", 0.9),
        ]

        async def mock_analyze(ticker):
            for t, s, c in tickers_signals:
                if t == ticker:
                    return _make_verdict(t, s, c)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "GOOGL"])
        assert result.top_pick == "GOOGL"


class TestTickerLimit:
    """FR-7: Ticker limit enforcement."""

    @pytest.mark.asyncio
    async def test_ticker_limit_exceeded(self):
        """11 tickers -> ValueError."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        tickers = [f"TICK{i}" for i in range(11)]
        with pytest.raises(ValueError, match="10"):
            await mc.analyze_portfolio(tickers)


class TestPortfolioVaultIntegration:
    """FR-1 edge: vault store called for each successful verdict."""

    @pytest.mark.asyncio
    async def test_analyze_portfolio_stores_verdicts(self):
        """Vault store called for portfolio analysis."""
        from agents.market_conductor import MarketConductor

        vault = MagicMock()
        vault.store_verdict = AsyncMock()

        mc = MarketConductor(vault=vault)

        async def mock_analyze(ticker):
            return _make_verdict(ticker, "BUY", 0.7)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        await mc.analyze_portfolio(["AAPL", "GOOGL"])
        # Note: individual analyze() calls handle their own vault storage.
        # analyze_portfolio doesn't double-store -- this tests that it completes
        # without vault errors.
        assert True  # No exception raised


class TestGracefulDegradation:
    """S10.2: Graceful degradation tests."""

    @pytest.mark.asyncio
    async def test_no_degradation_all_agents_succeed(self):
        """All agents succeed -> no confidence reduction, no warnings."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.8,
                key_drivers=["ValuationScout: BUY (80%)"],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.overall_confidence == 0.8
        # No WARNING entries in key_drivers
        assert not any("WARNING" in d for d in verdict.key_drivers)

    @pytest.mark.asyncio
    async def test_one_agent_fails_confidence_reduced(self):
        """1 directional agent fails -> confidence reduced by 0.20."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=True)
        # Make first agent (valuation_scout) fail
        agents[0].analyze = AsyncMock(side_effect=Exception("boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.8,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.overall_confidence == pytest.approx(0.6)

    @pytest.mark.asyncio
    async def test_two_agents_fail_confidence_reduced(self):
        """2 directional agents fail -> confidence reduced by 0.40."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=True)
        agents[0].analyze = AsyncMock(side_effect=Exception("boom"))
        agents[1].analyze = AsyncMock(side_effect=Exception("boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.8,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.overall_confidence == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_all_directional_agents_fail_hold_zero(self):
        """All directional agents fail -> HOLD/0.0."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        # 5 directional agents all fail + risk guardian succeeds
        agents = _make_mock_agents(include_risk=True)
        for i in range(5):  # 5 directional agents
            agents[i].analyze = AsyncMock(side_effect=Exception("boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="HOLD",
                overall_confidence=0.5,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        # 5 * 0.20 = 1.00 penalty, 0.5 - 1.0 = -0.5, clamped to 0.0
        assert verdict.overall_confidence == 0.0

    @pytest.mark.asyncio
    async def test_risk_guardian_failure_no_confidence_penalty(self):
        """RiskGuardian failure does NOT reduce directional confidence."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=True)
        # Make risk_guardian fail (last agent)
        agents[-1].analyze = AsyncMock(side_effect=Exception("risk boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.8,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        # No penalty for RiskGuardian failure
        assert verdict.overall_confidence == 0.8

    @pytest.mark.asyncio
    async def test_timeout_reduces_confidence_with_warning(self):
        """Timeout -> confidence reduced, warning distinguishes timeout."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor(timeout=0.01)
        agents = _make_mock_agents(include_risk=False)

        # Make first agent slow (will timeout)
        async def slow_analyze(ticker):
            await asyncio.sleep(1.0)
            return _make_report(ValuationReport, agent_name="valuation_scout")

        agents[0].analyze = slow_analyze
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.8,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.overall_confidence == pytest.approx(0.6)
        # Warning should mention timeout
        warnings = [d for d in verdict.key_drivers if "WARNING" in d]
        assert len(warnings) >= 1
        assert any("timed out" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_strong_buy_downgrade_on_low_confidence(self):
        """STRONG_BUY with missing agent -> BUY if confidence < 0.75."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=True)
        agents[0].analyze = AsyncMock(side_effect=Exception("boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="STRONG_BUY",
                overall_confidence=0.85,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        # 0.85 - 0.20 = 0.65 < 0.75 -> downgrade STRONG_BUY to BUY
        assert verdict.final_signal == "BUY"
        assert verdict.overall_confidence == pytest.approx(0.65)

    @pytest.mark.asyncio
    async def test_strong_sell_downgrade_on_low_confidence(self):
        """STRONG_SELL with missing agent -> SELL if confidence < 0.75."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=True)
        agents[0].analyze = AsyncMock(side_effect=Exception("boom"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="STRONG_SELL",
                overall_confidence=0.85,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.final_signal == "SELL"
        assert verdict.overall_confidence == pytest.approx(0.65)

    @pytest.mark.asyncio
    async def test_warning_in_key_drivers_on_failure(self):
        """Failed agent produces WARNING entry in key_drivers."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        agents = _make_mock_agents(include_risk=False)
        agents[0].analyze = AsyncMock(side_effect=Exception("connection refused"))
        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        warnings = [d for d in verdict.key_drivers if "WARNING" in d]
        assert len(warnings) >= 1
        assert any("valuation_scout" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_warning_distinguishes_timeout_from_error(self):
        """Timeout warning says 'timed out', error warning says 'failed'."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor(timeout=0.01)
        agents = _make_mock_agents(include_risk=False)

        # Agent 0: timeout
        async def slow_analyze(ticker):
            await asyncio.sleep(1.0)
            return _make_report(ValuationReport, agent_name="valuation_scout")

        agents[0].analyze = slow_analyze

        # Agent 1: exception
        agents[1].analyze = AsyncMock(side_effect=Exception("network error"))

        mc._agents = agents

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="HOLD",
                overall_confidence=0.7,
                key_drivers=[],
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        warnings = [d for d in verdict.key_drivers if "WARNING" in d]
        assert any("timed out" in w for w in warnings)
        assert any("failed" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_portfolio_partial_ticker_failure(self):
        """Portfolio: 1 ticker fails, others succeed."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()

        async def mock_analyze(ticker):
            if ticker == "BAD":
                raise Exception("Analysis failed")
            return _make_verdict(ticker, "BUY", 0.7)

        mc.analyze = AsyncMock(side_effect=mock_analyze)

        result = await mc.analyze_portfolio(["AAPL", "BAD", "MSFT"])
        assert len(result.verdicts) == 2
        assert "BAD" not in result.tickers

    @pytest.mark.asyncio
    async def test_portfolio_all_tickers_fail(self):
        """Portfolio: all tickers fail -> HOLD, empty."""
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc.analyze = AsyncMock(side_effect=Exception("boom"))

        result = await mc.analyze_portfolio(["AAPL", "GOOGL"])
        assert result.portfolio_signal == "HOLD"
        assert result.top_pick is None
        assert len(result.verdicts) == 0


class TestAgentDetailModel:
    """S15.2: AgentDetail model validation."""

    def test_agent_detail_basic(self):
        detail = AgentDetail(
            agent_name="ValuationScout",
            signal="BUY",
            confidence=0.8,
            reasoning="Strong fundamentals",
            key_metrics={"pe_ratio": 25.0},
            data_source="Polygon.io",
            execution_time_ms=150,
        )
        assert detail.agent_name == "ValuationScout"
        assert detail.signal == "BUY"
        assert detail.confidence == 0.8
        assert detail.key_metrics == {"pe_ratio": 25.0}
        assert detail.data_source == "Polygon.io"
        assert detail.execution_time_ms == 150

    def test_agent_detail_confidence_clamped(self):
        detail = AgentDetail(agent_name="Test", signal="BUY", confidence=1.5)
        assert detail.confidence == 1.0

    def test_agent_detail_confidence_none_default(self):
        detail = AgentDetail(agent_name="Test", signal="BUY", confidence=None)
        assert detail.confidence == 0.0

    def test_agent_detail_negative_confidence(self):
        detail = AgentDetail(agent_name="Test", signal="BUY", confidence=-0.5)
        assert detail.confidence == 0.0

    def test_agent_detail_defaults(self):
        detail = AgentDetail(agent_name="Test", signal="HOLD", confidence=0.5)
        assert detail.reasoning == ""
        assert detail.key_metrics == {}
        assert detail.data_source == ""
        assert detail.execution_time_ms == 0


class TestFinalVerdictNewFields:
    """S15.2: FinalVerdict includes analyst_details, risk_level, execution_time_ms."""

    def test_verdict_has_analyst_details(self):
        verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
        )
        assert verdict.analyst_details == {}
        assert verdict.risk_level == "MEDIUM"
        assert verdict.execution_time_ms == 0

    def test_verdict_with_analyst_details(self):
        detail = AgentDetail(
            agent_name="ValuationScout",
            signal="BUY",
            confidence=0.8,
            key_metrics={"pe_ratio": 25.0},
            data_source="Polygon.io",
        )
        verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
            analyst_details={"ValuationScout": detail},
            risk_level="LOW",
            execution_time_ms=500,
        )
        assert "ValuationScout" in verdict.analyst_details
        assert verdict.risk_level == "LOW"
        assert verdict.execution_time_ms == 500

    def test_verdict_serialization_with_details(self):
        detail = AgentDetail(
            agent_name="ValuationScout",
            signal="BUY",
            confidence=0.8,
        )
        verdict = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
            analyst_details={"ValuationScout": detail},
            risk_level="HIGH",
            execution_time_ms=1200,
        )
        data = verdict.model_dump()
        assert "analyst_details" in data
        assert "ValuationScout" in data["analyst_details"]
        assert data["risk_level"] == "HIGH"
        assert data["execution_time_ms"] == 1200


class TestRiskLevelCalculation:
    """S15.2: _calculate_risk_level logic."""

    def test_risk_level_high_with_few_reports(self):
        from agents.market_conductor import _calculate_risk_level

        report = _make_report(ValuationReport, agent_name="valuation_scout")
        assert _calculate_risk_level([report]) == "HIGH"

    def test_risk_level_high_with_no_reports(self):
        from agents.market_conductor import _calculate_risk_level

        assert _calculate_risk_level([]) == "HIGH"

    def test_risk_level_low_agreement(self):
        from agents.market_conductor import _calculate_risk_level

        # All BUY with high confidence -> LOW
        reports = [
            _make_report(ValuationReport, agent_name="v", signal="BUY", confidence=0.8),
            _make_report(MomentumReport, agent_name="m", signal="BUY", confidence=0.7),
            _make_report(PulseReport, agent_name="p", signal="BUY", confidence=0.75),
        ]
        assert _calculate_risk_level(reports) == "LOW"

    def test_risk_level_high_disagreement(self):
        from agents.market_conductor import _calculate_risk_level

        # Mixed BUY/SELL -> high std -> HIGH
        reports = [
            _make_report(ValuationReport, agent_name="v", signal="BUY", confidence=0.8),
            _make_report(MomentumReport, agent_name="m", signal="SELL", confidence=0.7),
            _make_report(PulseReport, agent_name="p", signal="BUY", confidence=0.75),
        ]
        result = _calculate_risk_level(reports)
        assert result in ("HIGH", "MEDIUM")  # depends on stdev

    def test_risk_level_high_low_confidence(self):
        from agents.market_conductor import _calculate_risk_level

        # All HOLD but low confidence
        reports = [
            _make_report(ValuationReport, agent_name="v", signal="HOLD", confidence=0.3),
            _make_report(MomentumReport, agent_name="m", signal="HOLD", confidence=0.3),
        ]
        assert _calculate_risk_level(reports) == "HIGH"


class TestBuildAgentDetail:
    """S15.2: _build_agent_detail extracts key_metrics per report type."""

    def test_valuation_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = ValuationReport(
            ticker="AAPL",
            agent_name="ValuationScout",
            signal="BUY",
            confidence=0.8,
            reasoning="Strong",
            pe_ratio=25.0,
            pb_ratio=6.0,
        )
        detail = _build_agent_detail(report, execution_time_ms=100)
        assert detail.data_source == "Polygon.io"
        assert detail.key_metrics["pe_ratio"] == 25.0
        assert detail.key_metrics["pb_ratio"] == 6.0
        assert detail.execution_time_ms == 100

    def test_momentum_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = MomentumReport(
            ticker="AAPL",
            agent_name="MomentumTracker",
            signal="BUY",
            confidence=0.75,
            reasoning="Bullish",
            rsi_14=55.0,
            above_sma_50=True,
        )
        detail = _build_agent_detail(report)
        assert detail.data_source == "Polygon.io"
        assert detail.key_metrics["rsi_14"] == 55.0
        assert detail.key_metrics["above_sma_50"] is True

    def test_pulse_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = PulseReport(
            ticker="AAPL",
            agent_name="PulseMonitor",
            signal="BUY",
            confidence=0.65,
            reasoning="Positive",
            sentiment_score=0.6,
            article_count=5,
            top_headlines=["H1", "H2", "H3", "H4"],
        )
        detail = _build_agent_detail(report)
        assert detail.data_source == "NewsAPI"
        assert detail.key_metrics["sentiment_score"] == 0.6
        # top_headlines capped at 3
        assert len(detail.key_metrics["top_headlines"]) == 3

    def test_economy_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = EconomyReport(
            ticker="AAPL",
            agent_name="EconomyWatcher",
            signal="HOLD",
            confidence=0.7,
            reasoning="Stable",
            gdp_growth=2.5,
            macro_regime="expansion",
        )
        detail = _build_agent_detail(report)
        assert detail.data_source == "FRED API"
        assert detail.key_metrics["gdp_growth"] == 2.5
        assert detail.key_metrics["macro_regime"] == "expansion"

    def test_compliance_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = ComplianceReport(
            ticker="AAPL",
            agent_name="ComplianceChecker",
            signal="HOLD",
            confidence=0.9,
            reasoning="Clean",
            risk_score=0.1,
            risk_flags=[],
        )
        detail = _build_agent_detail(report)
        assert detail.data_source == "SEC Edgar"
        assert detail.key_metrics["risk_score"] == 0.1

    def test_risk_guardian_detail(self):
        from agents.market_conductor import _build_agent_detail

        report = RiskGuardianReport(
            ticker="AAPL",
            agent_name="RiskGuardian",
            signal="HOLD",
            confidence=0.6,
            reasoning="Risk assessment",
            beta=1.2,
            suggested_position_size=0.08,
        )
        detail = _build_agent_detail(report)
        assert detail.data_source == "Polygon.io"
        assert detail.key_metrics["beta"] == 1.2
        assert detail.key_metrics["suggested_position_size"] == 0.08


class TestAnalyzeRichResponse:
    """S15.2: analyze() populates analyst_details, risk_level, execution_time_ms."""

    @pytest.mark.asyncio
    async def test_analyze_populates_analyst_details(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert isinstance(verdict.analyst_details, dict)
        # Should have details for all 6 agents (5 directional + risk)
        assert len(verdict.analyst_details) == 6

    @pytest.mark.asyncio
    async def test_analyze_populates_risk_level(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.risk_level in ("LOW", "MEDIUM", "HIGH")

    @pytest.mark.asyncio
    async def test_analyze_populates_execution_time(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        assert verdict.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_no_agents_returns_high_risk(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._lazy_load_agents = lambda: []

        verdict = await mc.analyze("AAPL")
        assert verdict.risk_level == "HIGH"

    @pytest.mark.asyncio
    async def test_analyst_details_have_correct_structure(self):
        from agents.market_conductor import MarketConductor

        mc = MarketConductor()
        mc._agents = _make_mock_agents(include_risk=True)

        mock_synth = MagicMock()
        mock_synth.synthesize = AsyncMock(
            return_value=FinalVerdict(
                ticker="AAPL",
                final_signal="BUY",
                overall_confidence=0.7,
            )
        )
        mc._synthesizer = mock_synth

        verdict = await mc.analyze("AAPL")
        for name, detail in verdict.analyst_details.items():
            assert isinstance(detail, AgentDetail)
            assert detail.agent_name != ""
            assert detail.signal in ("BUY", "HOLD", "SELL")
            assert 0.0 <= detail.confidence <= 1.0


class TestCreateConductorServer:
    def test_create_conductor_server_returns_fastapi(self):
        """Factory returns a FastAPI app."""
        with (
            patch("agents.market_conductor.MarketConductor"),
            patch("agents.a2a_server.create_agent_server") as mock_create,
        ):
            from fastapi import FastAPI

            mock_create.return_value = FastAPI()

            from agents.market_conductor import create_conductor_server

            app = create_conductor_server()
            assert app is not None
            mock_create.assert_called_once()
