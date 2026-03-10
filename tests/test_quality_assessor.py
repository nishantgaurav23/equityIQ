"""Tests for evaluation/quality_assessor.py -- Quality Assessor (S14.1)."""

import pytest

from config.data_contracts import FinalVerdict
from evaluation.quality_assessor import QualityAssessment, QualityAssessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_AGENT_NAMES = [
    "valuation_scout",
    "momentum_tracker",
    "pulse_monitor",
    "economy_watcher",
    "compliance_checker",
    "risk_guardian",
]


def _make_verdict(
    signals: dict[str, str] | None = None,
    overall_confidence: float = 0.70,
    agent_confidences: dict[str, float] | None = None,
    risk_summary: str = "moderate risk",
) -> FinalVerdict:
    """Build a FinalVerdict with controlled signals/confidences."""
    if signals is None:
        signals = {name: "BUY" for name in ALL_AGENT_NAMES}

    from config.data_contracts import AgentDetail

    analyst_details = {}
    for name, sig in signals.items():
        conf = (agent_confidences or {}).get(name, 0.70)
        analyst_details[name] = AgentDetail(
            agent_name=name,
            signal=sig,
            confidence=conf,
            reasoning="test",
        )

    return FinalVerdict(
        ticker="AAPL",
        final_signal="BUY",
        overall_confidence=overall_confidence,
        analyst_signals=signals,
        analyst_details=analyst_details,
        risk_summary=risk_summary,
        key_drivers=["test driver"],
        session_id="test-session",
    )


# ---------------------------------------------------------------------------
# FR-1: Completeness Scoring
# ---------------------------------------------------------------------------


class TestCompleteness:
    def test_completeness_all_agents(self):
        """All 6 agent signals present -> completeness 1.0."""
        assessor = QualityAssessor()
        verdict = _make_verdict()
        result = assessor.assess(verdict)
        assert result.completeness_score == pytest.approx(1.0)

    def test_completeness_missing_agents(self):
        """3 agents missing -> completeness ~0.50."""
        signals = {name: "BUY" for name in ALL_AGENT_NAMES[:3]}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert result.completeness_score == pytest.approx(0.5, abs=0.01)

    def test_completeness_no_agents(self):
        """Empty signals -> completeness 0.0."""
        assessor = QualityAssessor()
        verdict = _make_verdict(signals={})
        result = assessor.assess(verdict)
        assert result.completeness_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# FR-2: Consensus Scoring
# ---------------------------------------------------------------------------


class TestConsensus:
    def test_consensus_unanimous_buy(self):
        """All agents signal BUY -> consensus 1.0."""
        signals = {name: "BUY" for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert result.consensus_score == pytest.approx(1.0)

    def test_consensus_unanimous_sell(self):
        """All agents signal SELL -> consensus 1.0."""
        signals = {name: "SELL" for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert result.consensus_score == pytest.approx(1.0)

    def test_consensus_mixed_signals(self):
        """3 BUY + 3 SELL -> low consensus."""
        signals = {}
        for i, name in enumerate(ALL_AGENT_NAMES):
            signals[name] = "BUY" if i < 3 else "SELL"
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert result.consensus_score <= 0.50

    def test_consensus_single_agent(self):
        """One agent -> consensus 1.0."""
        signals = {"valuation_scout": "BUY"}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert result.consensus_score == pytest.approx(1.0)

    def test_consensus_no_agents(self):
        """No agents -> consensus 0.0."""
        assessor = QualityAssessor()
        verdict = _make_verdict(signals={})
        result = assessor.assess(verdict)
        assert result.consensus_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# FR-3: Calibration Scoring
# ---------------------------------------------------------------------------


class TestCalibration:
    def test_calibration_well_calibrated(self):
        """Overall close to mean agent confidence -> high score."""
        confs = {name: 0.70 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.70, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert result.calibration_score >= 0.90

    def test_calibration_overconfident(self):
        """Overall much higher than mean -> low score."""
        confs = {name: 0.40 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.90, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert result.calibration_score < 0.50

    def test_calibration_no_agent_confidences(self):
        """No agent details -> 0.5 neutral."""
        assessor = QualityAssessor()
        verdict = _make_verdict(signals={})
        result = assessor.assess(verdict)
        assert result.calibration_score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# FR-4: Overall Grade
# ---------------------------------------------------------------------------


class TestGrade:
    def test_grade_a(self):
        """Perfect verdict -> grade A."""
        confs = {name: 0.85 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.85, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert result.grade == "A"

    def test_grade_f(self):
        """Low scores -> grade F."""
        assessor = QualityAssessor()
        verdict = _make_verdict(signals={})
        result = assessor.assess(verdict)
        assert result.grade == "F"

    def test_grade_boundaries(self):
        """Scores at exact thresholds map correctly."""
        assessor = QualityAssessor()
        assert assessor._compute_grade(0.90) == "A"
        assert assessor._compute_grade(0.89) == "B"
        assert assessor._compute_grade(0.75) == "B"
        assert assessor._compute_grade(0.74) == "C"
        assert assessor._compute_grade(0.60) == "C"
        assert assessor._compute_grade(0.59) == "D"
        assert assessor._compute_grade(0.40) == "D"
        assert assessor._compute_grade(0.39) == "F"

    def test_overall_score_weighting(self):
        """Overall score uses correct weights: completeness 0.4, consensus 0.3, calibration 0.3."""
        assessor = QualityAssessor()
        # All agents, unanimous BUY, well-calibrated
        confs = {name: 0.80 for name in ALL_AGENT_NAMES}
        verdict = _make_verdict(overall_confidence=0.80, agent_confidences=confs)
        result = assessor.assess(verdict)
        expected = 1.0 * 0.4 + 1.0 * 0.3 + result.calibration_score * 0.3
        assert result.overall_score == pytest.approx(expected, abs=0.01)


# ---------------------------------------------------------------------------
# FR-5: Issue Detection
# ---------------------------------------------------------------------------


class TestIssues:
    def test_issues_missing_agents(self):
        """Missing agents listed in issues."""
        signals = {name: "BUY" for name in ALL_AGENT_NAMES[:3]}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert any("Missing agent" in issue for issue in result.issues)

    def test_issues_low_consensus(self):
        """Low consensus flagged."""
        signals = {}
        for i, name in enumerate(ALL_AGENT_NAMES):
            signals[name] = "BUY" if i < 3 else "SELL"
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert any("consensus" in issue.lower() for issue in result.issues)

    def test_issues_overconfidence(self):
        """Overconfidence flagged."""
        confs = {name: 0.40 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.90, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert any("inflated" in issue.lower() for issue in result.issues)

    def test_issues_underconfidence(self):
        """Underconfidence flagged."""
        confs = {name: 0.90 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.50, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert any("deflated" in issue.lower() for issue in result.issues)

    def test_issues_insufficient_coverage(self):
        """Fewer than 3 agents flagged."""
        signals = {"valuation_scout": "BUY", "momentum_tracker": "BUY"}
        assessor = QualityAssessor()
        verdict = _make_verdict(signals=signals)
        result = assessor.assess(verdict)
        assert any("Insufficient" in issue for issue in result.issues)

    def test_no_issues_perfect_verdict(self):
        """Perfect verdict has no issues."""
        confs = {name: 0.85 for name in ALL_AGENT_NAMES}
        assessor = QualityAssessor()
        verdict = _make_verdict(overall_confidence=0.85, agent_confidences=confs)
        result = assessor.assess(verdict)
        assert result.issues == []


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_assess_full_verdict(self):
        """End-to-end with realistic FinalVerdict."""
        signals = {
            "valuation_scout": "BUY",
            "momentum_tracker": "BUY",
            "pulse_monitor": "HOLD",
            "economy_watcher": "BUY",
            "compliance_checker": "HOLD",
            "risk_guardian": "HOLD",
        }
        confs = {
            "valuation_scout": 0.80,
            "momentum_tracker": 0.75,
            "pulse_monitor": 0.60,
            "economy_watcher": 0.70,
            "compliance_checker": 0.65,
            "risk_guardian": 0.55,
        }
        assessor = QualityAssessor()
        verdict = _make_verdict(
            signals=signals,
            overall_confidence=0.72,
            agent_confidences=confs,
        )
        result = assessor.assess(verdict)

        # Should be a complete, decent-quality analysis
        assert isinstance(result, QualityAssessment)
        assert result.completeness_score == pytest.approx(1.0)
        assert 0.0 <= result.consensus_score <= 1.0
        assert 0.0 <= result.calibration_score <= 1.0
        assert 0.0 <= result.overall_score <= 1.0
        assert result.grade in ("A", "B", "C", "D", "F")

    def test_assessment_scores_clamped(self):
        """All scores clamped to [0.0, 1.0]."""
        assessor = QualityAssessor()
        verdict = _make_verdict(signals={})
        result = assessor.assess(verdict)
        for score in [
            result.completeness_score,
            result.consensus_score,
            result.calibration_score,
            result.overall_score,
        ]:
            assert 0.0 <= score <= 1.0
