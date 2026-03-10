"""Tests for S15.2 -- Rich Analysis Response.

Validates AgentDetail model, risk_level calculation, execution_time_ms tracking,
and backward compatibility of analyst_signals dict.
"""

from __future__ import annotations

from agents.market_conductor import _build_agent_detail, _calculate_risk_level
from config.data_contracts import (
    AgentDetail,
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _report(cls, agent_name, signal="BUY", confidence=0.7, **kwargs):
    return cls(
        ticker="AAPL",
        agent_name=agent_name,
        signal=signal,
        confidence=confidence,
        reasoning="test reason",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# AgentDetail model
# ---------------------------------------------------------------------------

class TestAgentDetailModel:
    def test_agent_detail_has_all_fields(self):
        d = AgentDetail(
            agent_name="ValuationScout",
            signal="BUY",
            confidence=0.75,
            reasoning="Undervalued",
            key_metrics={"pe_ratio": 15.2},
            data_source="Polygon.io",
            execution_time_ms=1200,
        )
        assert d.agent_name == "ValuationScout"
        assert d.signal == "BUY"
        assert d.confidence == 0.75
        assert d.reasoning == "Undervalued"
        assert d.key_metrics == {"pe_ratio": 15.2}
        assert d.data_source == "Polygon.io"
        assert d.execution_time_ms == 1200

    def test_agent_detail_confidence_clamped(self):
        d = AgentDetail(agent_name="X", signal="BUY", confidence=1.5)
        assert d.confidence == 1.0
        d2 = AgentDetail(agent_name="X", signal="BUY", confidence=-0.5)
        assert d2.confidence == 0.0

    def test_agent_detail_defaults(self):
        d = AgentDetail(agent_name="X", signal="BUY", confidence=0.5)
        assert d.reasoning == ""
        assert d.key_metrics == {}
        assert d.data_source == ""
        assert d.execution_time_ms == 0


# ---------------------------------------------------------------------------
# FinalVerdict new fields
# ---------------------------------------------------------------------------

class TestFinalVerdictRichFields:
    def test_verdict_has_analyst_details_dict(self):
        v = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
            analyst_details={
                "ValuationScout": AgentDetail(
                    agent_name="ValuationScout", signal="BUY", confidence=0.8
                )
            },
        )
        assert "ValuationScout" in v.analyst_details
        assert v.analyst_details["ValuationScout"].signal == "BUY"

    def test_verdict_has_risk_level(self):
        v = FinalVerdict(
            ticker="AAPL", final_signal="HOLD", overall_confidence=0.5, risk_level="HIGH"
        )
        assert v.risk_level == "HIGH"

    def test_verdict_default_risk_level_medium(self):
        v = FinalVerdict(ticker="AAPL", final_signal="HOLD", overall_confidence=0.5)
        assert v.risk_level == "MEDIUM"

    def test_verdict_has_execution_time_ms(self):
        v = FinalVerdict(
            ticker="AAPL", final_signal="BUY", overall_confidence=0.7, execution_time_ms=3500
        )
        assert v.execution_time_ms == 3500

    def test_verdict_backward_compat_analyst_signals(self):
        v = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
            analyst_signals={"ValuationScout": "BUY", "MomentumTracker": "HOLD"},
            analyst_details={},
        )
        assert v.analyst_signals["ValuationScout"] == "BUY"
        assert isinstance(v.analyst_details, dict)


# ---------------------------------------------------------------------------
# Risk level calculation
# ---------------------------------------------------------------------------

class TestRiskLevelCalculation:
    def test_high_risk_signal_disagreement(self):
        """std > 0.6 → HIGH."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.8),
            _report(MomentumReport, "momentum_tracker", signal="SELL", confidence=0.8),
            _report(EconomyReport, "economy_watcher", signal="BUY", confidence=0.8),
        ]
        assert _calculate_risk_level(reports) == "HIGH"

    def test_high_risk_low_confidence(self):
        """avg confidence < 0.40 → HIGH."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.3),
            _report(MomentumReport, "momentum_tracker", signal="BUY", confidence=0.35),
        ]
        assert _calculate_risk_level(reports) == "HIGH"

    def test_medium_risk_moderate_disagreement(self):
        """std > 0.3 but <= 0.6 → MEDIUM."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.7),
            _report(MomentumReport, "momentum_tracker", signal="HOLD", confidence=0.7),
            _report(EconomyReport, "economy_watcher", signal="BUY", confidence=0.7),
        ]
        assert _calculate_risk_level(reports) == "MEDIUM"

    def test_medium_risk_moderate_confidence(self):
        """avg confidence < 0.60 → MEDIUM."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.55),
            _report(MomentumReport, "momentum_tracker", signal="BUY", confidence=0.5),
        ]
        assert _calculate_risk_level(reports) == "MEDIUM"

    def test_low_risk_agreement_high_confidence(self):
        """All agree + high confidence → LOW."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.8),
            _report(MomentumReport, "momentum_tracker", signal="BUY", confidence=0.75),
            _report(EconomyReport, "economy_watcher", signal="BUY", confidence=0.7),
        ]
        assert _calculate_risk_level(reports) == "LOW"

    def test_high_risk_single_report(self):
        """< 2 reports → HIGH."""
        reports = [
            _report(ValuationReport, "valuation_scout", signal="BUY", confidence=0.9),
        ]
        assert _calculate_risk_level(reports) == "HIGH"

    def test_high_risk_empty(self):
        assert _calculate_risk_level([]) == "HIGH"


# ---------------------------------------------------------------------------
# _build_agent_detail
# ---------------------------------------------------------------------------

class TestBuildAgentDetail:
    def test_valuation_detail_has_metrics(self):
        r = _report(
            ValuationReport, "valuation_scout", pe_ratio=15.0, pb_ratio=2.5
        )
        d = _build_agent_detail(r, execution_time_ms=500)
        assert d.data_source == "Polygon.io"
        assert d.key_metrics["pe_ratio"] == 15.0
        assert d.execution_time_ms == 500

    def test_momentum_detail_has_metrics(self):
        r = _report(MomentumReport, "momentum_tracker", rsi_14=65.0)
        d = _build_agent_detail(r)
        assert d.data_source == "Polygon.io"
        assert d.key_metrics["rsi_14"] == 65.0

    def test_pulse_detail_data_source(self):
        r = _report(PulseReport, "pulse_monitor", sentiment_score=0.5)
        d = _build_agent_detail(r)
        assert d.data_source == "NewsAPI"

    def test_economy_detail_data_source(self):
        r = _report(EconomyReport, "economy_watcher", gdp_growth=2.1)
        d = _build_agent_detail(r)
        assert d.data_source == "FRED API"

    def test_compliance_detail_data_source(self):
        r = _report(ComplianceReport, "compliance_checker", risk_score=0.3)
        d = _build_agent_detail(r)
        assert d.data_source == "SEC Edgar"

    def test_risk_guardian_detail_data_source(self):
        r = _report(RiskGuardianReport, "risk_guardian", beta=1.1)
        d = _build_agent_detail(r)
        assert d.data_source == "Polygon.io"

    def test_detail_preserves_reasoning(self):
        r = _report(ValuationReport, "valuation_scout")
        d = _build_agent_detail(r)
        assert d.reasoning == "test reason"
        assert d.signal == "BUY"
        assert d.confidence == 0.7


# ---------------------------------------------------------------------------
# Integration: execution_time_ms populated
# ---------------------------------------------------------------------------

class TestExecutionTimePopulated:
    def test_verdict_execution_time_positive(self):
        """Verify execution_time_ms field can be set and is int."""
        v = FinalVerdict(
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=0.7,
            execution_time_ms=4200,
        )
        assert v.execution_time_ms == 4200
        assert isinstance(v.execution_time_ms, int)
