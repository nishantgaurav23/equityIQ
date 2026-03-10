"""SignalSynthesizer -- Fuses 5 analyst signals into a FinalVerdict via XGBoost.

Receives AnalystReports from all 5 specialist agents plus a RiskGuardianReport,
runs signal fusion via SignalFusionModel, applies compliance override, and returns
a FinalVerdict with 5-level signal. Port 8006.
"""

from __future__ import annotations

import json
import logging
import uuid

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)
from models.signal_fusion import DEFAULT_WEIGHTS, SignalFusionModel

logger = logging.getLogger(__name__)

# Agent name -> report type for JSON deserialization
_REPORT_TYPE_MAP: dict[str, type] = {
    "ValuationScout": ValuationReport,
    "MomentumTracker": MomentumReport,
    "PulseMonitor": PulseReport,
    "EconomyWatcher": EconomyReport,
    "ComplianceChecker": ComplianceReport,
    "RiskGuardian": RiskGuardianReport,
}

# Module-level fusion model instance (shared across calls).
_fusion_model = SignalFusionModel()


def _fallback_verdict(
    ticker: str = "", reason: str = "", session_id: str | None = None
) -> FinalVerdict:
    """Safe HOLD/0.0 fallback verdict."""
    return FinalVerdict(
        ticker=ticker,
        final_signal="HOLD",
        overall_confidence=0.0,
        reasoning=reason,
        session_id=session_id or str(uuid.uuid4()),
    )


def _parse_reports_from_json(reports_json: str) -> list:
    """Parse a JSON string into a list of typed AnalystReport subclasses."""
    raw = json.loads(reports_json)
    if not isinstance(raw, list):
        return []

    reports = []
    for item in raw:
        agent_name = item.get("agent_name", "")
        report_cls = _REPORT_TYPE_MAP.get(agent_name)
        if report_cls:
            try:
                reports.append(report_cls.model_validate(item))
            except Exception:
                logger.warning("Failed to parse report for agent %s", agent_name)
        else:
            logger.warning("Unknown agent_name in report: %s", agent_name)
    return reports


def _format_risk_summary(risk_report: RiskGuardianReport) -> str:
    """Format a RiskGuardianReport into a human-readable summary string."""
    parts = []
    if risk_report.beta is not None:
        parts.append(f"Beta: {risk_report.beta:.2f}")
    if risk_report.annualized_volatility is not None:
        parts.append(f"Volatility: {risk_report.annualized_volatility:.2f}")
    if risk_report.max_drawdown is not None:
        parts.append(f"Max Drawdown: {risk_report.max_drawdown:.2f}")
    if risk_report.suggested_position_size is not None:
        parts.append(f"Position Size: {risk_report.suggested_position_size:.2f}")
    if risk_report.sharpe_ratio is not None:
        parts.append(f"Sharpe: {risk_report.sharpe_ratio:.2f}")
    if risk_report.var_95 is not None:
        parts.append(f"VaR 95%: {risk_report.var_95:.2f}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# Tool function for ADK agent
# ---------------------------------------------------------------------------


async def synthesize_signals(reports_json: str) -> dict:
    """Parse analyst reports from JSON and produce a FinalVerdict dict.

    This is the ADK tool function exposed to the LLM agent.
    """
    try:
        reports = _parse_reports_from_json(reports_json)
        if not reports:
            return _fallback_verdict().model_dump()

        model = SignalFusionModel()
        verdict = model.predict(reports)
        return verdict.model_dump()
    except Exception as exc:
        logger.warning("synthesize_signals failed: %s", exc)
        return _fallback_verdict(reason=str(exc)).model_dump()


# ---------------------------------------------------------------------------
# SignalSynthesizer agent class
# ---------------------------------------------------------------------------


class SignalSynthesizer(BaseAnalystAgent):
    """Specialist agent for fusing analyst signals into a final investment verdict."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="signal_synthesizer",
            output_schema=FinalVerdict,
            tools=[synthesize_signals],
            model=model,
        )

    async def synthesize(
        self,
        reports: list,
        risk_report: RiskGuardianReport | None = None,
        session_id: str | None = None,
    ) -> FinalVerdict:
        """Deterministic signal fusion -- bypasses the LLM.

        This is the primary path used by MarketConductor. Uses SignalFusionModel
        with weight adjustments and compliance override.

        Args:
            reports: List of AnalystReport subclass instances.
            risk_report: Optional RiskGuardianReport for risk summary.
            session_id: Optional session ID for request tracing (threaded to predict).
        """
        try:
            if not reports:
                return _fallback_verdict(session_id=session_id)

            ticker = reports[0].ticker

            # Adjust weights based on macro regime (FR-5)
            adjusted_weights = self._get_adjusted_weights(reports)
            fusion = SignalFusionModel(weights=adjusted_weights)

            verdict = fusion.predict(reports, session_id=session_id)

            # Populate risk summary if provided (FR-4)
            if risk_report is not None:
                verdict.risk_summary = _format_risk_summary(risk_report)

            return verdict

        except Exception as exc:
            logger.warning("SignalSynthesizer.synthesize failed: %s", exc)
            ticker = reports[0].ticker if reports else ""
            return _fallback_verdict(ticker=ticker, reason=str(exc))

    def _get_adjusted_weights(self, reports: list) -> dict[str, float]:
        """Return signal weights, adjusting for macro regime if needed (FR-5).

        If EconomyReport has macro_regime of 'contraction' or 'stagflation',
        increase EconomyWatcher weight to 0.30 and redistribute proportionally.
        """
        weights = dict(DEFAULT_WEIGHTS)

        # Find EconomyReport
        economy_report = None
        for r in reports:
            if isinstance(r, EconomyReport):
                economy_report = r
                break

        if economy_report is None:
            return weights

        regime = economy_report.macro_regime
        if regime not in ("contraction", "stagflation"):
            return weights

        # Increase EconomyWatcher to 0.30
        current_econ = weights.get("EconomyWatcher", 0.20)
        target_econ = 0.30
        delta = target_econ - current_econ

        if delta <= 0:
            return weights

        # Redistribute delta proportionally from other agents
        other_keys = [k for k in weights if k != "EconomyWatcher"]
        other_total = sum(weights[k] for k in other_keys)

        for k in other_keys:
            reduction = delta * (weights[k] / other_total)
            weights[k] -= reduction

        weights["EconomyWatcher"] = target_econ
        return weights


# ---------------------------------------------------------------------------
# Factory + module-level singleton
# ---------------------------------------------------------------------------


def create_signal_synthesizer() -> SignalSynthesizer:
    """Factory function to create a SignalSynthesizer instance."""
    return SignalSynthesizer()


signal_synthesizer = create_signal_synthesizer()
