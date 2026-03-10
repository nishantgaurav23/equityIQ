"""Quality scoring for analysis verdicts (S14.1).

Evaluates data completeness, signal consensus, and confidence calibration.
Returns a quality grade from A to F.
"""

from collections import Counter

from pydantic import BaseModel, field_validator

from config.data_contracts import FinalVerdict

# The 6 expected agent signal sources
EXPECTED_AGENTS = [
    "valuation_scout",
    "momentum_tracker",
    "pulse_monitor",
    "economy_watcher",
    "compliance_checker",
    "risk_guardian",
]

# Weighting for overall score
WEIGHT_COMPLETENESS = 0.40
WEIGHT_CONSENSUS = 0.30
WEIGHT_CALIBRATION = 0.30


class QualityAssessment(BaseModel):
    """Result of quality assessment on a FinalVerdict."""

    completeness_score: float
    consensus_score: float
    calibration_score: float
    overall_score: float
    grade: str
    issues: list[str] = []

    @field_validator(
        "completeness_score",
        "consensus_score",
        "calibration_score",
        "overall_score",
        mode="before",
    )
    @classmethod
    def clamp_score(cls, v):
        return max(0.0, min(1.0, float(v)))


class QualityAssessor:
    """Scores the quality of a FinalVerdict analysis."""

    def assess(self, verdict: FinalVerdict) -> QualityAssessment:
        """Run all quality checks and return a QualityAssessment."""
        completeness = self._score_completeness(verdict)
        consensus = self._score_consensus(verdict)
        calibration = self._score_calibration(verdict)

        overall = (
            completeness * WEIGHT_COMPLETENESS
            + consensus * WEIGHT_CONSENSUS
            + calibration * WEIGHT_CALIBRATION
        )
        overall = max(0.0, min(1.0, overall))

        grade = self._compute_grade(overall)
        issues = self._detect_issues(verdict, completeness, consensus, calibration)

        return QualityAssessment(
            completeness_score=completeness,
            consensus_score=consensus,
            calibration_score=calibration,
            overall_score=overall,
            grade=grade,
            issues=issues,
        )

    def _score_completeness(self, verdict: FinalVerdict) -> float:
        """FR-1: Score how many expected agents are present."""
        if not verdict.analyst_signals:
            return 0.0
        present = sum(1 for name in EXPECTED_AGENTS if name in verdict.analyst_signals)
        return present / len(EXPECTED_AGENTS)

    def _score_consensus(self, verdict: FinalVerdict) -> float:
        """FR-2: Measure agreement among agent signals."""
        signals = list(verdict.analyst_signals.values())
        if not signals:
            return 0.0
        if len(signals) == 1:
            return 1.0

        counts = Counter(signals)
        # Consensus = fraction of agents agreeing with the majority signal
        majority_count = max(counts.values())
        return majority_count / len(signals)

    def _score_calibration(self, verdict: FinalVerdict) -> float:
        """FR-3: Assess confidence calibration."""
        if not verdict.analyst_details:
            return 0.5  # neutral when no data

        agent_confs = [d.confidence for d in verdict.analyst_details.values()]
        if not agent_confs:
            return 0.5

        mean_conf = sum(agent_confs) / len(agent_confs)
        deviation = abs(verdict.overall_confidence - mean_conf)

        # Score decreases linearly with deviation; 0.5 deviation -> score 0.0
        score = max(0.0, 1.0 - (deviation / 0.5))
        return score

    def _compute_grade(self, overall_score: float) -> str:
        """FR-4: Map overall score to letter grade."""
        if overall_score >= 0.90:
            return "A"
        if overall_score >= 0.75:
            return "B"
        if overall_score >= 0.60:
            return "C"
        if overall_score >= 0.40:
            return "D"
        return "F"

    def _detect_issues(
        self,
        verdict: FinalVerdict,
        completeness: float,
        consensus: float,
        calibration: float,
    ) -> list[str]:
        """FR-5: Identify specific quality problems."""
        issues: list[str] = []

        # Missing agents
        if completeness < 1.0:
            missing = [n for n in EXPECTED_AGENTS if n not in verdict.analyst_signals]
            if missing:
                issues.append(f"Missing agent signals: {', '.join(missing)}")

        # Insufficient coverage
        agent_count = len(verdict.analyst_signals)
        if agent_count < 3:
            issues.append("Insufficient agent coverage for reliable analysis")

        # Low consensus
        if consensus <= 0.50:
            issues.append("Low signal consensus -- agents disagree significantly")

        # Calibration issues
        if verdict.analyst_details:
            agent_confs = [d.confidence for d in verdict.analyst_details.values()]
            if agent_confs:
                mean_conf = sum(agent_confs) / len(agent_confs)
                if verdict.overall_confidence > mean_conf + 0.20:
                    issues.append("Overall confidence may be inflated")
                elif verdict.overall_confidence < mean_conf - 0.20:
                    issues.append("Overall confidence may be deflated")

        return issues
