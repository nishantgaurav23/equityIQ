"""MarketConductor -- orchestrator that runs all agents in parallel and fuses signals.

Coordinates the 5 directional analysts + RiskGuardian, feeds results through
SignalSynthesizer, stores the verdict in InsightVault, and returns a FinalVerdict.
Port 8000.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from typing import TYPE_CHECKING

from config.data_contracts import (
    AgentDetail,
    AnalystReport,
    CompanyInfo,
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PortfolioInsight,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)
from models.signal_fusion import MISSING_AGENT_PENALTY

if TYPE_CHECKING:
    from memory.insight_vault import InsightVault

logger = logging.getLogger(__name__)

# Default per-agent timeout in seconds.
DEFAULT_AGENT_TIMEOUT: float = 60.0

MAX_PORTFOLIO_TICKERS: int = 10

# Names of the 5 directional agents (not RiskGuardian).
_DIRECTIONAL_AGENT_NAMES: set[str] = {
    "valuation_scout",
    "momentum_tracker",
    "pulse_monitor",
    "economy_watcher",
    "compliance_checker",
}

# Signal -> numeric score mapping for portfolio aggregation.
_SIGNAL_SCORE: dict[str, int] = {
    "STRONG_BUY": 2,
    "BUY": 1,
    "HOLD": 0,
    "SELL": -1,
    "STRONG_SELL": -2,
}


def _compute_portfolio_signal(verdicts: list[FinalVerdict]) -> str:
    """Compute an aggregate portfolio signal from individual verdicts.

    Uses confidence-weighted average of signal scores, mapped back to a 5-level signal.
    STRONG_BUY/STRONG_SELL requires max individual confidence >= 0.75.
    """
    if not verdicts:
        return "HOLD"

    total_weight = sum(v.overall_confidence for v in verdicts)
    if total_weight == 0:
        return "HOLD"

    weighted_sum = sum(_SIGNAL_SCORE[v.final_signal] * v.overall_confidence for v in verdicts)
    avg_score = weighted_sum / total_weight
    max_confidence = max(v.overall_confidence for v in verdicts)

    if avg_score >= 1.5 and max_confidence >= 0.75:
        return "STRONG_BUY"
    elif avg_score >= 0.5:
        return "BUY"
    elif avg_score > -0.5:
        return "HOLD"
    elif avg_score > -1.5:
        return "SELL"
    elif max_confidence >= 0.75:
        return "STRONG_SELL"
    else:
        return "SELL"


def _compute_diversification_score(verdicts: list[FinalVerdict]) -> float:
    """Calculate diversification score based on signal diversity.

    Score = (unique_signals - 1) / (total_verdicts - 1), clamped to [0.0, 1.0].
    Single ticker or empty -> 0.0.
    """
    if len(verdicts) <= 1:
        return 0.0
    unique_signals = len({v.final_signal for v in verdicts})
    score = (unique_signals - 1) / (len(verdicts) - 1)
    return max(0.0, min(1.0, score))


def _select_top_pick(verdicts: list[FinalVerdict]) -> str | None:
    """Select the ticker with highest confidence among BUY/STRONG_BUY verdicts."""
    buy_verdicts = [v for v in verdicts if v.final_signal in ("BUY", "STRONG_BUY")]
    if not buy_verdicts:
        return None
    return max(buy_verdicts, key=lambda v: v.overall_confidence).ticker


# Maps agent_name (from BaseAnalystAgent) -> report class & display name
_AGENT_NAME_MAP: dict[str, tuple[type[AnalystReport], str]] = {
    "valuation_scout": (ValuationReport, "ValuationScout"),
    "momentum_tracker": (MomentumReport, "MomentumTracker"),
    "pulse_monitor": (PulseReport, "PulseMonitor"),
    "economy_watcher": (EconomyReport, "EconomyWatcher"),
    "compliance_checker": (ComplianceReport, "ComplianceChecker"),
    "risk_guardian": (RiskGuardianReport, "RiskGuardian"),
}


def _calculate_risk_level(reports: list[AnalystReport]) -> str:
    """Calculate risk level from agent signal agreement and confidence."""
    if len(reports) < 2:
        return "HIGH"

    signal_map = {"BUY": 1.0, "HOLD": 0.0, "SELL": -1.0}
    signals = [signal_map.get(r.signal, 0.0) for r in reports]
    confidences = [r.confidence for r in reports]

    signal_std = statistics.stdev(signals) if len(signals) > 1 else 1.0
    avg_confidence = statistics.mean(confidences) if confidences else 0.0

    if signal_std > 0.6 or avg_confidence < 0.40:
        return "HIGH"
    elif signal_std > 0.3 or avg_confidence < 0.60:
        return "MEDIUM"
    return "LOW"


def _build_agent_detail(report: AnalystReport, execution_time_ms: int = 0) -> AgentDetail:
    """Convert an AnalystReport to AgentDetail for API response."""
    key_metrics: dict = {}
    data_source = ""

    if isinstance(report, ValuationReport):
        key_metrics = {
            k: v
            for k, v in {
                "pe_ratio": report.pe_ratio,
                "pb_ratio": report.pb_ratio,
                "revenue_growth": report.revenue_growth,
                "debt_to_equity": report.debt_to_equity,
                "fcf_yield": report.fcf_yield,
                "intrinsic_value_gap": report.intrinsic_value_gap,
            }.items()
            if v is not None
        }
        data_source = "Polygon.io"
    elif isinstance(report, MomentumReport):
        key_metrics = {
            k: v
            for k, v in {
                "rsi_14": report.rsi_14,
                "macd_signal": report.macd_signal,
                "above_sma_50": report.above_sma_50,
                "above_sma_200": report.above_sma_200,
                "volume_trend": report.volume_trend,
                "price_momentum_score": report.price_momentum_score,
            }.items()
            if v is not None
        }
        data_source = "Polygon.io"
    elif isinstance(report, PulseReport):
        key_metrics = {
            k: v
            for k, v in {
                "sentiment_score": report.sentiment_score,
                "article_count": report.article_count,
                "top_headlines": (report.top_headlines[:3] if report.top_headlines else []),
                "event_flags": report.event_flags,
            }.items()
            if v is not None
        }
        data_source = "NewsAPI"
    elif isinstance(report, EconomyReport):
        key_metrics = {
            k: v
            for k, v in {
                "gdp_growth": report.gdp_growth,
                "inflation_rate": report.inflation_rate,
                "fed_funds_rate": report.fed_funds_rate,
                "unemployment_rate": report.unemployment_rate,
                "macro_regime": report.macro_regime,
            }.items()
            if v is not None
        }
        data_source = "FRED API"
    elif isinstance(report, ComplianceReport):
        key_metrics = {
            k: v
            for k, v in {
                "latest_filing_type": report.latest_filing_type,
                "days_since_filing": report.days_since_filing,
                "risk_flags": report.risk_flags,
                "risk_score": report.risk_score,
            }.items()
            if v is not None
        }
        data_source = "SEC Edgar"
    elif isinstance(report, RiskGuardianReport):
        key_metrics = {
            k: v
            for k, v in {
                "beta": report.beta,
                "annualized_volatility": report.annualized_volatility,
                "sharpe_ratio": report.sharpe_ratio,
                "max_drawdown": report.max_drawdown,
                "suggested_position_size": report.suggested_position_size,
                "var_95": report.var_95,
            }.items()
            if v is not None
        }
        data_source = "Polygon.io"

    return AgentDetail(
        agent_name=report.agent_name,
        signal=report.signal,
        confidence=report.confidence,
        reasoning=report.reasoning,
        key_metrics=key_metrics,
        data_source=data_source,
        execution_time_ms=execution_time_ms,
    )


def _estimate_price_target(
    reports: list[AnalystReport], ticker: str, weighted_signal: float = 0.0
) -> float | None:
    """Estimate price target from current price and weighted signal.

    Uses the approach: price_target = current_price * (1 + weighted_signal * 0.20)
    This bounds the adjustment to ±20% from current price.

    Falls back to intrinsic_value_gap if available and weighted_signal is zero.
    Returns None if current price cannot be determined.
    """
    # Try to get current price from Yahoo Finance
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if hist.empty:
            return None
        current_price = float(hist["Close"].iloc[-1])
    except Exception:
        logger.debug("Could not fetch current price for %s", ticker)
        return None

    # Primary: use weighted signal for bounded ±20% adjustment
    if weighted_signal != 0.0:
        adjustment = weighted_signal * 0.20
        target = current_price * (1.0 + adjustment)
        return round(target, 2)

    # Fallback: use intrinsic_value_gap if available, clamped to ±50%
    for r in reports:
        if isinstance(r, ValuationReport) and r.intrinsic_value_gap is not None:
            gap = max(-0.50, min(0.50, r.intrinsic_value_gap))
            target = current_price * (1.0 + gap)
            return round(target, 2)

    return None


class MarketConductor:
    """Orchestrator that runs all specialist agents in parallel and fuses signals."""

    def __init__(
        self,
        vault: InsightVault | None = None,
        timeout: float = DEFAULT_AGENT_TIMEOUT,
    ) -> None:
        self._vault = vault
        self._timeout = timeout
        self._agents: list = []
        self._synthesizer = None  # Lazy-loaded to avoid circular imports

    def _get_synthesizer(self):
        """Lazy-load SignalSynthesizer to avoid circular import issues."""
        if self._synthesizer is None:
            from agents.signal_synthesizer import SignalSynthesizer

            self._synthesizer = SignalSynthesizer()
        return self._synthesizer

    def _lazy_load_agents(self) -> list:
        """Import agents lazily to avoid module-level ADK init issues."""
        if self._agents:
            return self._agents

        try:
            from agents.valuation_scout import ValuationScout

            self._agents.append(ValuationScout())
        except Exception:
            logger.warning("Failed to load ValuationScout")

        try:
            from agents.momentum_tracker import MomentumTrackerAgent

            self._agents.append(MomentumTrackerAgent())
        except Exception:
            logger.warning("Failed to load MomentumTrackerAgent")

        try:
            from agents.pulse_monitor import PulseMonitorAgent

            self._agents.append(PulseMonitorAgent())
        except Exception:
            logger.warning("Failed to load PulseMonitorAgent")

        try:
            from agents.economy_watcher import EconomyWatcher

            self._agents.append(EconomyWatcher())
        except Exception:
            logger.warning("Failed to load EconomyWatcher")

        try:
            from agents.compliance_checker import ComplianceCheckerAgent

            self._agents.append(ComplianceCheckerAgent())
        except Exception:
            logger.warning("Failed to load ComplianceCheckerAgent")

        try:
            from agents.risk_guardian import RiskGuardian

            self._agents.append(RiskGuardian())
        except Exception:
            logger.warning("Failed to load RiskGuardian")

        return self._agents

    async def _run_agent_with_timeout(self, agent, ticker: str) -> tuple[AnalystReport, int]:
        """Run a single agent with timeout. Returns (report, execution_time_ms).

        Raises asyncio.TimeoutError on timeout.
        """
        start = time.perf_counter()
        result = await asyncio.wait_for(agent.analyze(ticker), timeout=self._timeout)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return result, elapsed_ms

    async def analyze(self, ticker: str, session_id: str | None = None) -> FinalVerdict:
        """Run all agents in parallel for *ticker* and return a fused FinalVerdict.

        Each agent has a per-agent timeout (default 30s). Agents that fail or
        timeout return nothing -- missing agents reduce confidence via
        SignalFusionModel's MISSING_AGENT_PENALTY.

        Args:
            ticker: Stock ticker symbol.
            session_id: Optional session ID for request tracing. Generated if None.
        """
        import uuid

        overall_start = time.perf_counter()
        ticker = ticker.strip().upper()
        session_id = session_id or str(uuid.uuid4())
        logger.info("Analyzing %s (session=%s)", ticker, session_id)
        agents = self._lazy_load_agents()

        if not agents:
            logger.error("No agents available for analysis (session=%s)", session_id)
            return FinalVerdict(
                ticker=ticker,
                final_signal="HOLD",
                overall_confidence=0.0,
                key_drivers=["No agents available"],
                session_id=session_id,
                risk_level="HIGH",
            )

        # Run all agents + company info fetch in parallel
        tasks = [self._run_agent_with_timeout(agent, ticker) for agent in agents]

        async def _fetch_company_info() -> CompanyInfo | None:
            try:
                from tools.yahoo_connector import yahoo

                raw = await yahoo.get_company_info(ticker)
                if raw:
                    return CompanyInfo(**{k: v for k, v in raw.items() if v is not None})
            except Exception:
                logger.debug("Could not fetch company info for %s", ticker)
            return None

        company_info_task = asyncio.create_task(_fetch_company_info())
        results = await asyncio.gather(*tasks, return_exceptions=True)
        company_info = await company_info_task

        # Separate successful reports from failures; track degradation warnings.
        reports: list[AnalystReport] = []
        all_reports: list[AnalystReport] = []  # includes risk for risk_level calc
        risk_report: RiskGuardianReport | None = None
        failure_warnings: list[str] = []
        missing_directional: int = 0
        agent_timings: dict[str, int] = {}  # agent_name -> execution_time_ms

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = agents[i].name if i < len(agents) else "unknown"
                if isinstance(result, asyncio.TimeoutError):
                    logger.warning("Agent %s timed out after %.1fs", agent_name, self._timeout)
                    failure_warnings.append(
                        f"WARNING: {agent_name} timed out after {self._timeout:.1f}s"
                    )
                else:
                    logger.warning("Agent %s raised: %s", agent_name, result)
                    failure_warnings.append(f"WARNING: {agent_name} failed: {result}")
                # Only penalize directional agents, not RiskGuardian.
                if agent_name in _DIRECTIONAL_AGENT_NAMES:
                    missing_directional += 1
                continue

            # Unpack tuple (report, execution_time_ms)
            if isinstance(result, tuple) and len(result) == 2:
                report, exec_time = result
            else:
                # Backward compat: bare AnalystReport (e.g. in tests)
                report = result
                exec_time = 0

            if isinstance(report, AnalystReport):
                # Remap agent_name to display name for fusion model compatibility
                display_name = _AGENT_NAME_MAP.get(report.agent_name, (None, report.agent_name))[1]
                report.agent_name = display_name
                agent_timings[display_name] = exec_time
                all_reports.append(report)

                if isinstance(report, RiskGuardianReport):
                    risk_report = report
                else:
                    reports.append(report)

        # Fuse directional signals via SignalSynthesizer
        synthesizer = self._get_synthesizer()
        verdict = await synthesizer.synthesize(
            reports, risk_report=risk_report, session_id=session_id
        )
        verdict.ticker = ticker
        verdict.session_id = session_id
        verdict.company_info = company_info

        # --- Rich analysis response (S15.2) ---
        # Build analyst_details from all successful reports
        analyst_details: dict[str, AgentDetail] = {}
        for report in all_reports:
            detail = _build_agent_detail(
                report, execution_time_ms=agent_timings.get(report.agent_name, 0)
            )
            analyst_details[report.agent_name] = detail
        verdict.analyst_details = analyst_details

        # Calculate risk_level from directional reports
        verdict.risk_level = _calculate_risk_level(reports)

        # Compute price_target using weighted signal (bounded ±20% from current price)
        signal_score = _SIGNAL_SCORE.get(verdict.final_signal, 0)
        # Normalize signal score from [-2, 2] to [-1, 1] range
        weighted_signal = signal_score / 2.0 * verdict.overall_confidence
        verdict.price_target = _estimate_price_target(
            all_reports, ticker, weighted_signal=weighted_signal
        )

        # Set total execution time
        verdict.execution_time_ms = int((time.perf_counter() - overall_start) * 1000)

        # --- Graceful degradation (S10.2) ---
        # Reduce confidence by MISSING_AGENT_PENALTY per missing directional agent.
        if missing_directional > 0:
            penalty = missing_directional * MISSING_AGENT_PENALTY
            verdict.overall_confidence = max(0.0, min(1.0, verdict.overall_confidence - penalty))

        # Downgrade STRONG signals when confidence drops below 0.75.
        if verdict.overall_confidence < 0.75:
            if verdict.final_signal == "STRONG_BUY":
                verdict.final_signal = "BUY"
            elif verdict.final_signal == "STRONG_SELL":
                verdict.final_signal = "SELL"

        # Append failure warnings to key_drivers.
        if failure_warnings:
            verdict.key_drivers = (verdict.key_drivers or []) + failure_warnings

        # Store verdict if vault is available
        if self._vault:
            try:
                await self._vault.store_verdict(verdict)
            except Exception:
                logger.warning("Failed to store verdict for %s", ticker)

        return verdict

    async def analyze_portfolio(
        self, tickers: list[str], session_id: str | None = None
    ) -> PortfolioInsight:
        """Run analyze() for each ticker and aggregate into a PortfolioInsight.

        Tickers are normalized (stripped, uppercased) and deduplicated.
        Maximum 10 tickers allowed. All analyses run concurrently.
        """
        # Normalize and deduplicate tickers (preserve first-occurrence order)
        seen: set[str] = set()
        clean_tickers: list[str] = []
        for t in tickers:
            normalized = t.strip().upper()
            if normalized and normalized not in seen:
                seen.add(normalized)
                clean_tickers.append(normalized)

        if len(clean_tickers) > MAX_PORTFOLIO_TICKERS:
            raise ValueError(
                f"Maximum {MAX_PORTFOLIO_TICKERS} tickers allowed, got {len(clean_tickers)}"
            )

        if not clean_tickers:
            return PortfolioInsight(
                tickers=[],
                verdicts=[],
                portfolio_signal="HOLD",
                diversification_score=0.0,
                top_pick=None,
            )

        logger.info(
            "Starting portfolio analysis for %d tickers: %s (session=%s)",
            len(clean_tickers),
            clean_tickers,
            session_id,
        )

        # Run all ticker analyses concurrently
        tasks = [self.analyze(t) for t in clean_tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect successful verdicts
        verdicts: list[FinalVerdict] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("Portfolio analysis failed for %s: %s", clean_tickers[i], result)
                continue
            if isinstance(result, FinalVerdict):
                verdicts.append(result)

        successful_tickers = [v.ticker for v in verdicts]

        return PortfolioInsight(
            tickers=successful_tickers,
            verdicts=verdicts,
            portfolio_signal=_compute_portfolio_signal(verdicts),
            diversification_score=_compute_diversification_score(verdicts),
            top_pick=_select_top_pick(verdicts),
        )


def create_conductor_server():
    """Factory function to create an A2A-compatible FastAPI server for MarketConductor.

    Returns a FastAPI app on port 8000 with agent card, health, and A2A endpoints.
    """
    from agents.a2a_server import create_agent_server
    from agents.base_agent import BaseAnalystAgent

    # MarketConductor is not a BaseAnalystAgent itself, so we create a thin wrapper
    # that delegates analyze() to the conductor instance.
    conductor = MarketConductor()

    class _ConductorAgentAdapter(BaseAnalystAgent):
        """Adapter to expose MarketConductor via A2A server protocol."""

        def __init__(self) -> None:
            # Bypass normal BaseAnalystAgent init -- conductor is not a standard agent.
            self._name = "market_conductor"
            self._persona = "Market Conductor: orchestrates all specialist agents."
            self._output_schema = FinalVerdict
            self._tools = []
            self._agent = None  # No ADK agent needed

        async def analyze(self, ticker: str) -> FinalVerdict:
            return await conductor.analyze(ticker)

    adapter = _ConductorAgentAdapter()
    return create_agent_server(adapter)
