"""Tests for agents/signal_synthesizer.py -- SignalSynthesizer fusion agent."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)

# ---------------------------------------------------------------------------
# Helpers -- build typed reports for tests
# ---------------------------------------------------------------------------


def _valuation(signal="BUY", confidence=0.8):
    return ValuationReport(
        ticker="AAPL",
        agent_name="ValuationScout",
        signal=signal,
        confidence=confidence,
        reasoning="test",
        pe_ratio=25.0,
        pb_ratio=5.0,
        revenue_growth=0.1,
        debt_to_equity=1.0,
        fcf_yield=0.05,
        intrinsic_value_gap=0.15,
    )


def _momentum(signal="BUY", confidence=0.7):
    return MomentumReport(
        ticker="AAPL",
        agent_name="MomentumTracker",
        signal=signal,
        confidence=confidence,
        reasoning="test",
        rsi_14=55.0,
        macd_signal=0.5,
        above_sma_50=True,
        above_sma_200=True,
        price_momentum_score=0.6,
    )


def _pulse(signal="BUY", confidence=0.75):
    return PulseReport(
        ticker="AAPL",
        agent_name="PulseMonitor",
        signal=signal,
        confidence=confidence,
        reasoning="test",
        sentiment_score=0.6,
        article_count=10,
        top_headlines=["Good news"],
    )


def _economy(signal="BUY", confidence=0.7, macro_regime="expansion"):
    return EconomyReport(
        ticker="AAPL",
        agent_name="EconomyWatcher",
        signal=signal,
        confidence=confidence,
        reasoning="test",
        gdp_growth=2.5,
        inflation_rate=2.0,
        fed_funds_rate=5.0,
        unemployment_rate=3.5,
        macro_regime=macro_regime,
    )


def _compliance(signal="BUY", confidence=0.8, risk_flags=None):
    return ComplianceReport(
        ticker="AAPL",
        agent_name="ComplianceChecker",
        signal=signal,
        confidence=confidence,
        reasoning="test",
        latest_filing_type="10-K",
        days_since_filing=30,
        risk_flags=risk_flags or [],
        risk_score=0.1,
    )


def _risk_report():
    return RiskGuardianReport(
        ticker="AAPL",
        agent_name="RiskGuardian",
        signal="HOLD",
        confidence=0.6,
        reasoning="test",
        beta=1.2,
        annualized_volatility=0.25,
        sharpe_ratio=1.5,
        max_drawdown=-0.15,
        suggested_position_size=0.05,
        var_95=0.03,
    )


def _all_buy_reports():
    return [_valuation(), _momentum(), _pulse(), _economy(), _compliance()]


def _all_sell_reports():
    return [
        _valuation("SELL", 0.8),
        _momentum("SELL", 0.7),
        _pulse("SELL", 0.75),
        _economy("SELL", 0.7),
        _compliance("SELL", 0.8),
    ]


def _mixed_reports():
    return [
        _valuation("BUY", 0.8),
        _momentum("SELL", 0.6),
        _pulse("HOLD", 0.5),
        _economy("BUY", 0.7),
        _compliance("HOLD", 0.6),
    ]


# ---------------------------------------------------------------------------
# T1: Construction (FR-1)
# ---------------------------------------------------------------------------


class TestConstruction:
    """SignalSynthesizer instantiation and properties."""

    def test_signal_synthesizer_construction(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        assert synth.name == "signal_synthesizer"

    def test_output_schema_is_final_verdict(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        assert synth._output_schema is FinalVerdict

    def test_has_tools(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        tool_names = [fn.__name__ for fn in synth._tools]
        assert "synthesize_signals" in tool_names


# ---------------------------------------------------------------------------
# T2: Synthesize -- all BUY (FR-3)
# ---------------------------------------------------------------------------


class TestSynthesizeAllBuy:
    """All 5 agents signal BUY -> BUY or STRONG_BUY verdict."""

    @pytest.mark.asyncio
    async def test_synthesize_all_reports_buy(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        verdict = await synth.synthesize(reports)

        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"
        assert verdict.final_signal in ("BUY", "STRONG_BUY")
        assert verdict.overall_confidence > 0.0


# ---------------------------------------------------------------------------
# T3: Synthesize -- all SELL (FR-3)
# ---------------------------------------------------------------------------


class TestSynthesizeAllSell:
    """All 5 agents signal SELL -> SELL or STRONG_SELL verdict."""

    @pytest.mark.asyncio
    async def test_synthesize_all_reports_sell(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_sell_reports()
        verdict = await synth.synthesize(reports)

        assert isinstance(verdict, FinalVerdict)
        assert verdict.final_signal in ("SELL", "STRONG_SELL")


# ---------------------------------------------------------------------------
# T4: Synthesize -- mixed signals (FR-3)
# ---------------------------------------------------------------------------


class TestSynthesizeMixed:
    """Mixed signals produce a valid verdict."""

    @pytest.mark.asyncio
    async def test_synthesize_mixed_reports(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _mixed_reports()
        verdict = await synth.synthesize(reports)

        assert isinstance(verdict, FinalVerdict)
        assert verdict.final_signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
        assert 0.0 <= verdict.overall_confidence <= 1.0


# ---------------------------------------------------------------------------
# T5: Synthesize -- empty reports (FR-3)
# ---------------------------------------------------------------------------


class TestSynthesizeEmpty:
    """Empty report list -> HOLD with confidence 0.0."""

    @pytest.mark.asyncio
    async def test_synthesize_empty_reports(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        verdict = await synth.synthesize([])

        assert verdict.final_signal == "HOLD"
        assert verdict.overall_confidence == 0.0


# ---------------------------------------------------------------------------
# T6: Compliance override -- going_concern (FR-6)
# ---------------------------------------------------------------------------


class TestComplianceOverrideGoingConcern:
    """going_concern in risk_flags -> forces SELL."""

    @pytest.mark.asyncio
    async def test_compliance_override_going_concern(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        # Replace compliance with going_concern flag
        reports[-1] = _compliance("BUY", 0.8, risk_flags=["going_concern"])
        verdict = await synth.synthesize(reports)

        assert verdict.final_signal == "SELL"


# ---------------------------------------------------------------------------
# T7: Compliance override -- restatement (FR-6)
# ---------------------------------------------------------------------------


class TestComplianceOverrideRestatement:
    """restatement in risk_flags -> forces SELL."""

    @pytest.mark.asyncio
    async def test_compliance_override_restatement(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        reports[-1] = _compliance("BUY", 0.8, risk_flags=["restatement"])
        verdict = await synth.synthesize(reports)

        assert verdict.final_signal == "SELL"


# ---------------------------------------------------------------------------
# T8: Compliance override -- no flags (FR-6)
# ---------------------------------------------------------------------------


class TestComplianceOverrideNoFlags:
    """Clean compliance -> no override, BUY stays BUY."""

    @pytest.mark.asyncio
    async def test_compliance_override_no_flags(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        verdict = await synth.synthesize(reports)

        # Should NOT be overridden to SELL
        assert verdict.final_signal in ("BUY", "STRONG_BUY")


# ---------------------------------------------------------------------------
# T9: Risk summary integration (FR-4)
# ---------------------------------------------------------------------------


class TestRiskSummary:
    """RiskGuardianReport populates risk_summary."""

    @pytest.mark.asyncio
    async def test_risk_summary_integration(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        risk = _risk_report()
        verdict = await synth.synthesize(reports, risk_report=risk)

        assert verdict.risk_summary != ""
        assert "beta" in verdict.risk_summary.lower() or "1.2" in verdict.risk_summary
        assert "volatility" in verdict.risk_summary.lower() or "0.25" in verdict.risk_summary

    @pytest.mark.asyncio
    async def test_risk_summary_none(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()
        verdict = await synth.synthesize(reports, risk_report=None)

        assert verdict.risk_summary == ""


# ---------------------------------------------------------------------------
# T10: Weight adjustment (FR-5)
# ---------------------------------------------------------------------------


class TestWeightAdjustment:
    """Macro regime affects signal weights."""

    @pytest.mark.asyncio
    async def test_weight_adjustment_contraction(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = [
            _valuation(),
            _momentum(),
            _pulse(),
            _economy("SELL", 0.8, macro_regime="contraction"),
            _compliance(),
        ]
        # The contraction regime should increase EconomyWatcher weight
        # We verify by checking the method returns adjusted weights
        weights = synth._get_adjusted_weights(reports)
        assert weights["EconomyWatcher"] == pytest.approx(0.30, abs=0.01)

    @pytest.mark.asyncio
    async def test_weight_adjustment_stagflation(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = [
            _valuation(),
            _momentum(),
            _pulse(),
            _economy("SELL", 0.7, macro_regime="stagflation"),
            _compliance(),
        ]
        weights = synth._get_adjusted_weights(reports)
        assert weights["EconomyWatcher"] == pytest.approx(0.30, abs=0.01)

    @pytest.mark.asyncio
    async def test_weight_adjustment_expansion(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = [
            _valuation(),
            _momentum(),
            _pulse(),
            _economy("BUY", 0.7, macro_regime="expansion"),
            _compliance(),
        ]
        weights = synth._get_adjusted_weights(reports)
        assert weights["EconomyWatcher"] == pytest.approx(0.20, abs=0.01)


# ---------------------------------------------------------------------------
# T11: Missing agents (FR-3)
# ---------------------------------------------------------------------------


class TestMissingAgents:
    """Fewer than 5 reports -> reduced confidence."""

    @pytest.mark.asyncio
    async def test_synthesize_missing_agents(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        # Only 3 of 5 reports
        reports = [_valuation(), _momentum(), _pulse()]
        verdict = await synth.synthesize(reports)

        assert isinstance(verdict, FinalVerdict)
        # Confidence should be reduced due to missing agents
        all_verdict = await synth.synthesize(_all_buy_reports())
        assert verdict.overall_confidence < all_verdict.overall_confidence


# ---------------------------------------------------------------------------
# T12: Error handling (FR-8)
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Exception in model -> fallback HOLD/0.0."""

    @pytest.mark.asyncio
    async def test_synthesize_error_handling(self):
        from agents.signal_synthesizer import SignalSynthesizer

        synth = SignalSynthesizer()
        reports = _all_buy_reports()

        with patch(
            "agents.signal_synthesizer.SignalFusionModel.predict",
            side_effect=Exception("model crashed"),
        ):
            verdict = await synth.synthesize(reports)

        assert verdict.final_signal == "HOLD"
        assert verdict.overall_confidence == 0.0


# ---------------------------------------------------------------------------
# T13: Factory function and module singleton (FR-7)
# ---------------------------------------------------------------------------


class TestFactory:
    """Factory function and module-level singleton."""

    def test_factory_function(self):
        from agents.signal_synthesizer import create_signal_synthesizer

        synth = create_signal_synthesizer()
        assert synth.name == "signal_synthesizer"

    def test_module_singleton(self):
        from agents.signal_synthesizer import signal_synthesizer

        assert signal_synthesizer is not None
        assert signal_synthesizer.name == "signal_synthesizer"


# ---------------------------------------------------------------------------
# T14: Synthesize tool function (FR-2)
# ---------------------------------------------------------------------------


class TestSynthesizeToolFunction:
    """Module-level synthesize_signals tool function."""

    @pytest.mark.asyncio
    async def test_synthesize_signals_valid_json(self):
        import json

        from agents.signal_synthesizer import synthesize_signals

        reports_data = [
            {
                "ticker": "AAPL",
                "agent_name": "ValuationScout",
                "signal": "BUY",
                "confidence": 0.8,
                "reasoning": "test",
                "pe_ratio": 25.0,
            },
            {
                "ticker": "AAPL",
                "agent_name": "MomentumTracker",
                "signal": "BUY",
                "confidence": 0.7,
                "reasoning": "test",
                "rsi_14": 55.0,
            },
        ]
        result = await synthesize_signals(json.dumps(reports_data))
        assert isinstance(result, dict)
        assert "final_signal" in result
        assert "overall_confidence" in result

    @pytest.mark.asyncio
    async def test_synthesize_signals_invalid_json(self):
        from agents.signal_synthesizer import synthesize_signals

        result = await synthesize_signals("not valid json {{{")
        assert isinstance(result, dict)
        assert result["final_signal"] == "HOLD"
        assert result["overall_confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_synthesize_signals_empty_list(self):
        from agents.signal_synthesizer import synthesize_signals

        result = await synthesize_signals("[]")
        assert result["final_signal"] == "HOLD"
        assert result["overall_confidence"] == 0.0
