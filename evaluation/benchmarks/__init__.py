"""Benchmark test cases for validating agent pipeline outputs (S14.2).

Provides 10 well-known stock benchmarks with expected signal ranges,
a runner to validate pipeline outputs, and quality grade checking.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, field_validator, model_validator

from config.data_contracts import (
    AgentDetail,
    ComplianceReport,
    EconomyReport,
    MomentumReport,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)
from evaluation.quality_assessor import QualityAssessor
from models.signal_fusion import SignalFusionModel

logger = logging.getLogger(__name__)

# Grade ordinal ranking (higher = better)
GRADE_RANK: dict[str, int] = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}

# Mapping from PascalCase (SignalFusionModel) to snake_case (QualityAssessor)
_PASCAL_TO_SNAKE: dict[str, str] = {
    "ValuationScout": "valuation_scout",
    "MomentumTracker": "momentum_tracker",
    "PulseMonitor": "pulse_monitor",
    "EconomyWatcher": "economy_watcher",
    "ComplianceChecker": "compliance_checker",
    "RiskGuardian": "risk_guardian",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BenchmarkCase(BaseModel):
    """A single benchmark test case with expected outcome ranges."""

    ticker: str
    description: str
    reports: list  # List of AnalystReport subclass instances
    expected_signals: list[str]
    expected_confidence_min: float
    expected_confidence_max: float
    expected_min_grade: str = "C"

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("expected_confidence_min", "expected_confidence_max", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        return max(0.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def validate_expected_signals(self):
        if not self.expected_signals:
            raise ValueError("expected_signals must contain at least one expected signal")
        return self


class BenchmarkResult(BaseModel):
    """Result of running a single benchmark case."""

    ticker: str
    passed: bool
    actual_signal: str | None = None
    actual_confidence: float | None = None
    actual_grade: str | None = None
    expected_signals: list[str] = []
    expected_confidence_range: tuple[float, float] = (0.0, 1.0)
    expected_min_grade: str = "C"
    issues: list[str] = []
    error: str | None = None


class BenchmarkSuiteResult(BaseModel):
    """Aggregated result of running all benchmark cases."""

    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[BenchmarkResult] = []


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class BenchmarkRunner:
    """Executes benchmark cases through the signal pipeline and validates results."""

    def __init__(self):
        self._synthesizer = SignalFusionModel()
        self._assessor = QualityAssessor()

    def run_case(self, case: BenchmarkCase) -> BenchmarkResult:
        """Run a single benchmark case and validate against expected ranges."""
        issues: list[str] = []

        try:
            # Separate RiskGuardian from synthesis reports
            synth_reports = [r for r in case.reports if r.agent_name != "RiskGuardian"]

            # Run through synthesizer
            verdict = self._synthesizer.predict(synth_reports, session_id="benchmark")

            # Remap analyst_signals to snake_case and add RiskGuardian for QualityAssessor
            snake_signals: dict[str, str] = {}
            snake_details: dict[str, AgentDetail] = {}
            for r in case.reports:
                snake_name = _PASCAL_TO_SNAKE.get(r.agent_name, r.agent_name)
                snake_signals[snake_name] = r.signal
                snake_details[snake_name] = AgentDetail(
                    agent_name=snake_name,
                    signal=r.signal,
                    confidence=r.confidence,
                    reasoning=r.reasoning,
                )

            verdict.analyst_signals = snake_signals
            verdict.analyst_details = snake_details

            actual_signal = verdict.final_signal
            actual_confidence = verdict.overall_confidence

            # Quality assessment
            assessment = self._assessor.assess(verdict)
            actual_grade = assessment.grade

            # Validate
            signal_ok = self._validate_signal(actual_signal, case.expected_signals)
            if not signal_ok:
                issues.append(f"Signal {actual_signal} not in expected {case.expected_signals}")

            conf_ok = self._validate_confidence(
                actual_confidence, case.expected_confidence_min, case.expected_confidence_max
            )
            if not conf_ok:
                issues.append(
                    f"Confidence {actual_confidence:.3f} outside "
                    f"[{case.expected_confidence_min}, {case.expected_confidence_max}]"
                )

            grade_ok = self._validate_grade(actual_grade, case.expected_min_grade)
            if not grade_ok:
                issues.append(f"Grade {actual_grade} below minimum {case.expected_min_grade}")

            passed = signal_ok and conf_ok and grade_ok

            return BenchmarkResult(
                ticker=case.ticker,
                passed=passed,
                actual_signal=actual_signal,
                actual_confidence=actual_confidence,
                actual_grade=actual_grade,
                expected_signals=case.expected_signals,
                expected_confidence_range=(
                    case.expected_confidence_min,
                    case.expected_confidence_max,
                ),
                expected_min_grade=case.expected_min_grade,
                issues=issues,
            )

        except Exception as e:
            logger.error("Benchmark %s failed with error: %s", case.ticker, e)
            return BenchmarkResult(
                ticker=case.ticker,
                passed=False,
                expected_signals=case.expected_signals,
                expected_confidence_range=(
                    case.expected_confidence_min,
                    case.expected_confidence_max,
                ),
                expected_min_grade=case.expected_min_grade,
                issues=[f"Exception: {e}"],
                error=str(e),
            )

    def run_suite(self, cases: list[BenchmarkCase]) -> BenchmarkSuiteResult:
        """Run all benchmark cases and return aggregated results."""
        results = [self.run_case(case) for case in cases]
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed
        pass_rate = passed / len(results) if results else 0.0

        return BenchmarkSuiteResult(
            total=len(results),
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            results=results,
        )

    @staticmethod
    def _validate_signal(actual: str, expected: list[str]) -> bool:
        """Check if actual signal is within expected list."""
        return actual in expected

    @staticmethod
    def _validate_confidence(actual: float, min_conf: float, max_conf: float) -> bool:
        """Check if confidence falls within [min, max] range."""
        return min_conf <= actual <= max_conf

    @staticmethod
    def _validate_grade(actual: str, min_grade: str) -> bool:
        """Check if actual grade meets minimum (ordinal comparison)."""
        return GRADE_RANK.get(actual, 0) >= GRADE_RANK.get(min_grade, 0)


# ---------------------------------------------------------------------------
# Benchmark Suite: 10 well-known stocks
# ---------------------------------------------------------------------------


def _make_benchmark_suite() -> list[BenchmarkCase]:
    """Build the 10-stock benchmark suite with realistic mock data."""

    cases = []

    # 1. AAPL -- Large-cap tech, strong fundamentals, typically BUY/HOLD
    cases.append(
        BenchmarkCase(
            ticker="AAPL",
            description="Large-cap tech, strong fundamentals",
            reports=[
                ValuationReport(
                    ticker="AAPL",
                    agent_name="ValuationScout",
                    signal="BUY",
                    confidence=0.72,
                    reasoning="Strong FCF, reasonable P/E for growth",
                    pe_ratio=28.5,
                    pb_ratio=45.0,
                    revenue_growth=0.08,
                    debt_to_equity=1.5,
                    fcf_yield=0.035,
                    intrinsic_value_gap=0.10,
                ),
                MomentumReport(
                    ticker="AAPL",
                    agent_name="MomentumTracker",
                    signal="BUY",
                    confidence=0.68,
                    reasoning="Above both SMAs, positive MACD",
                    rsi_14=58.0,
                    macd_signal=0.5,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="increasing",
                    price_momentum_score=0.4,
                ),
                PulseReport(
                    ticker="AAPL",
                    agent_name="PulseMonitor",
                    signal="BUY",
                    confidence=0.65,
                    reasoning="Positive sentiment on product launches",
                    sentiment_score=0.35,
                    article_count=12,
                    top_headlines=["Apple AI features boost sales"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="AAPL",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Expansion but rate concerns",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="AAPL",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.70,
                    reasoning="Clean filing history",
                    latest_filing_type="10-K",
                    days_since_filing=45,
                    risk_flags=[],
                    risk_score=0.15,
                ),
                RiskGuardianReport(
                    ticker="AAPL",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.65,
                    reasoning="Moderate beta, stable",
                    beta=1.15,
                    annualized_volatility=0.22,
                    sharpe_ratio=1.2,
                    max_drawdown=-0.18,
                    suggested_position_size=0.08,
                    var_95=0.025,
                ),
            ],
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.40,
            expected_confidence_max=0.85,
            expected_min_grade="C",
        )
    )

    # 2. TSLA -- High-volatility growth, mixed signals
    cases.append(
        BenchmarkCase(
            ticker="TSLA",
            description="High-volatility growth, mixed signals",
            reports=[
                ValuationReport(
                    ticker="TSLA",
                    agent_name="ValuationScout",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="High P/E but strong growth",
                    pe_ratio=65.0,
                    pb_ratio=15.0,
                    revenue_growth=0.20,
                    debt_to_equity=0.8,
                    fcf_yield=0.01,
                    intrinsic_value_gap=-0.15,
                ),
                MomentumReport(
                    ticker="TSLA",
                    agent_name="MomentumTracker",
                    signal="BUY",
                    confidence=0.60,
                    reasoning="Strong momentum, above SMA 50",
                    rsi_14=62.0,
                    macd_signal=1.2,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="increasing",
                    price_momentum_score=0.5,
                ),
                PulseReport(
                    ticker="TSLA",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.50,
                    reasoning="Mixed sentiment",
                    sentiment_score=0.10,
                    article_count=20,
                    top_headlines=["Tesla delivery numbers mixed"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="TSLA",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Growth-sensitive in rate environment",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="TSLA",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.65,
                    reasoning="No major concerns",
                    latest_filing_type="10-K",
                    days_since_filing=60,
                    risk_flags=[],
                    risk_score=0.25,
                ),
                RiskGuardianReport(
                    ticker="TSLA",
                    agent_name="RiskGuardian",
                    signal="SELL",
                    confidence=0.60,
                    reasoning="High volatility, high beta",
                    beta=1.95,
                    annualized_volatility=0.55,
                    sharpe_ratio=0.6,
                    max_drawdown=-0.45,
                    suggested_position_size=0.04,
                    var_95=0.055,
                ),
            ],
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.30,
            expected_confidence_max=0.75,
            expected_min_grade="D",
        )
    )

    # 3. JPM -- Blue-chip financials, stable
    cases.append(
        BenchmarkCase(
            ticker="JPM",
            description="Blue-chip financials, stable HOLD/BUY",
            reports=[
                ValuationReport(
                    ticker="JPM",
                    agent_name="ValuationScout",
                    signal="BUY",
                    confidence=0.70,
                    reasoning="Low P/E, strong earnings",
                    pe_ratio=11.5,
                    pb_ratio=1.6,
                    revenue_growth=0.05,
                    debt_to_equity=2.5,
                    fcf_yield=0.06,
                    intrinsic_value_gap=0.12,
                ),
                MomentumReport(
                    ticker="JPM",
                    agent_name="MomentumTracker",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Consolidating near SMAs",
                    rsi_14=52.0,
                    macd_signal=0.1,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="stable",
                    price_momentum_score=0.15,
                ),
                PulseReport(
                    ticker="JPM",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Neutral bank sector news",
                    sentiment_score=0.05,
                    article_count=8,
                    top_headlines=["JPMorgan earnings beat estimates"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="JPM",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.65,
                    reasoning="Rate environment mixed for banks",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="JPM",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.75,
                    reasoning="Strong compliance track record",
                    latest_filing_type="10-K",
                    days_since_filing=30,
                    risk_flags=[],
                    risk_score=0.10,
                ),
                RiskGuardianReport(
                    ticker="JPM",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.65,
                    reasoning="Moderate beta, financial sector",
                    beta=1.10,
                    annualized_volatility=0.20,
                    sharpe_ratio=1.1,
                    max_drawdown=-0.20,
                    suggested_position_size=0.07,
                    var_95=0.022,
                ),
            ],
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.40,
            expected_confidence_max=0.80,
            expected_min_grade="C",
        )
    )

    # 4. AMZN -- Large-cap tech/retail, growth-oriented
    cases.append(
        BenchmarkCase(
            ticker="AMZN",
            description="Large-cap tech/retail, growth BUY",
            reports=[
                ValuationReport(
                    ticker="AMZN",
                    agent_name="ValuationScout",
                    signal="BUY",
                    confidence=0.68,
                    reasoning="AWS growth, improving margins",
                    pe_ratio=55.0,
                    pb_ratio=8.0,
                    revenue_growth=0.12,
                    debt_to_equity=0.6,
                    fcf_yield=0.02,
                    intrinsic_value_gap=0.08,
                ),
                MomentumReport(
                    ticker="AMZN",
                    agent_name="MomentumTracker",
                    signal="BUY",
                    confidence=0.65,
                    reasoning="Strong uptrend",
                    rsi_14=60.0,
                    macd_signal=0.8,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="increasing",
                    price_momentum_score=0.45,
                ),
                PulseReport(
                    ticker="AMZN",
                    agent_name="PulseMonitor",
                    signal="BUY",
                    confidence=0.62,
                    reasoning="Positive on AI/cloud growth",
                    sentiment_score=0.30,
                    article_count=15,
                    top_headlines=["AWS AI revenue surges"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="AMZN",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.58,
                    reasoning="Consumer spending resilient",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="AMZN",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.70,
                    reasoning="No compliance issues",
                    latest_filing_type="10-K",
                    days_since_filing=50,
                    risk_flags=[],
                    risk_score=0.12,
                ),
                RiskGuardianReport(
                    ticker="AMZN",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Growth stock volatility",
                    beta=1.25,
                    annualized_volatility=0.28,
                    sharpe_ratio=1.0,
                    max_drawdown=-0.25,
                    suggested_position_size=0.06,
                    var_95=0.030,
                ),
            ],
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.40,
            expected_confidence_max=0.80,
            expected_min_grade="C",
        )
    )

    # 5. JNJ -- Defensive healthcare, conservative
    cases.append(
        BenchmarkCase(
            ticker="JNJ",
            description="Defensive healthcare, conservative HOLD/BUY",
            reports=[
                ValuationReport(
                    ticker="JNJ",
                    agent_name="ValuationScout",
                    signal="HOLD",
                    confidence=0.65,
                    reasoning="Fair value, steady dividends",
                    pe_ratio=22.0,
                    pb_ratio=5.5,
                    revenue_growth=0.03,
                    debt_to_equity=0.4,
                    fcf_yield=0.04,
                    intrinsic_value_gap=0.02,
                ),
                MomentumReport(
                    ticker="JNJ",
                    agent_name="MomentumTracker",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Flat trend, low momentum",
                    rsi_14=48.0,
                    macd_signal=-0.1,
                    above_sma_50=False,
                    above_sma_200=True,
                    volume_trend="stable",
                    price_momentum_score=0.0,
                ),
                PulseReport(
                    ticker="JNJ",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.58,
                    reasoning="Steady healthcare news",
                    sentiment_score=0.05,
                    article_count=6,
                    top_headlines=["JNJ dividend increase announced"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="JNJ",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Defensive in any regime",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="JNJ",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.72,
                    reasoning="Strong compliance",
                    latest_filing_type="10-K",
                    days_since_filing=40,
                    risk_flags=[],
                    risk_score=0.08,
                ),
                RiskGuardianReport(
                    ticker="JNJ",
                    agent_name="RiskGuardian",
                    signal="BUY",
                    confidence=0.65,
                    reasoning="Low beta, defensive",
                    beta=0.65,
                    annualized_volatility=0.14,
                    sharpe_ratio=0.9,
                    max_drawdown=-0.12,
                    suggested_position_size=0.09,
                    var_95=0.015,
                ),
            ],
            expected_signals=["HOLD", "BUY"],
            expected_confidence_min=0.35,
            expected_confidence_max=0.75,
            expected_min_grade="C",
        )
    )

    # 6. NVDA -- AI/semiconductor momentum
    cases.append(
        BenchmarkCase(
            ticker="NVDA",
            description="AI/semiconductor momentum, strong BUY",
            reports=[
                ValuationReport(
                    ticker="NVDA",
                    agent_name="ValuationScout",
                    signal="BUY",
                    confidence=0.70,
                    reasoning="Revenue growth justifies premium",
                    pe_ratio=60.0,
                    pb_ratio=30.0,
                    revenue_growth=0.80,
                    debt_to_equity=0.4,
                    fcf_yield=0.015,
                    intrinsic_value_gap=0.05,
                ),
                MomentumReport(
                    ticker="NVDA",
                    agent_name="MomentumTracker",
                    signal="BUY",
                    confidence=0.75,
                    reasoning="Strong uptrend, high RSI",
                    rsi_14=68.0,
                    macd_signal=2.5,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="increasing",
                    price_momentum_score=0.8,
                ),
                PulseReport(
                    ticker="NVDA",
                    agent_name="PulseMonitor",
                    signal="BUY",
                    confidence=0.70,
                    reasoning="AI hype sustained",
                    sentiment_score=0.60,
                    article_count=25,
                    top_headlines=["NVIDIA data center revenue triples"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="NVDA",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Tech spending resilient",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="NVDA",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.68,
                    reasoning="No compliance issues",
                    latest_filing_type="10-K",
                    days_since_filing=55,
                    risk_flags=[],
                    risk_score=0.15,
                ),
                RiskGuardianReport(
                    ticker="NVDA",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="High beta, semiconductor risk",
                    beta=1.70,
                    annualized_volatility=0.45,
                    sharpe_ratio=1.5,
                    max_drawdown=-0.35,
                    suggested_position_size=0.05,
                    var_95=0.048,
                ),
            ],
            expected_signals=["BUY", "STRONG_BUY"],
            expected_confidence_min=0.45,
            expected_confidence_max=0.85,
            expected_min_grade="C",
        )
    )

    # 7. XOM -- Energy/cyclical, macro-sensitive
    cases.append(
        BenchmarkCase(
            ticker="XOM",
            description="Energy/cyclical, macro-sensitive",
            reports=[
                ValuationReport(
                    ticker="XOM",
                    agent_name="ValuationScout",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Fair value at current oil prices",
                    pe_ratio=12.0,
                    pb_ratio=2.0,
                    revenue_growth=-0.05,
                    debt_to_equity=0.3,
                    fcf_yield=0.07,
                    intrinsic_value_gap=0.0,
                ),
                MomentumReport(
                    ticker="XOM",
                    agent_name="MomentumTracker",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Sideways movement",
                    rsi_14=50.0,
                    macd_signal=-0.2,
                    above_sma_50=False,
                    above_sma_200=True,
                    volume_trend="stable",
                    price_momentum_score=-0.05,
                ),
                PulseReport(
                    ticker="XOM",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Oil price uncertainty",
                    sentiment_score=-0.05,
                    article_count=10,
                    top_headlines=["Oil prices stabilize amid OPEC talks"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="XOM",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Energy demand steady",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="XOM",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.70,
                    reasoning="Standard compliance",
                    latest_filing_type="10-K",
                    days_since_filing=35,
                    risk_flags=[],
                    risk_score=0.12,
                ),
                RiskGuardianReport(
                    ticker="XOM",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Cyclical risk, moderate beta",
                    beta=0.90,
                    annualized_volatility=0.25,
                    sharpe_ratio=0.8,
                    max_drawdown=-0.22,
                    suggested_position_size=0.07,
                    var_95=0.028,
                ),
            ],
            expected_signals=["HOLD", "BUY"],
            expected_confidence_min=0.35,
            expected_confidence_max=0.75,
            expected_min_grade="C",
        )
    )

    # 8. META -- Large-cap tech, sentiment-driven
    cases.append(
        BenchmarkCase(
            ticker="META",
            description="Large-cap tech, sentiment-driven",
            reports=[
                ValuationReport(
                    ticker="META",
                    agent_name="ValuationScout",
                    signal="BUY",
                    confidence=0.68,
                    reasoning="Strong ad revenue, low P/E for tech",
                    pe_ratio=22.0,
                    pb_ratio=6.5,
                    revenue_growth=0.22,
                    debt_to_equity=0.3,
                    fcf_yield=0.04,
                    intrinsic_value_gap=0.15,
                ),
                MomentumReport(
                    ticker="META",
                    agent_name="MomentumTracker",
                    signal="BUY",
                    confidence=0.65,
                    reasoning="Uptrend intact",
                    rsi_14=59.0,
                    macd_signal=0.6,
                    above_sma_50=True,
                    above_sma_200=True,
                    volume_trend="increasing",
                    price_momentum_score=0.35,
                ),
                PulseReport(
                    ticker="META",
                    agent_name="PulseMonitor",
                    signal="BUY",
                    confidence=0.60,
                    reasoning="AI investments well received",
                    sentiment_score=0.25,
                    article_count=14,
                    top_headlines=["Meta AI assistant gains traction"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="META",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.58,
                    reasoning="Ad spending depends on economy",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="META",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.68,
                    reasoning="Regulatory scrutiny but manageable",
                    latest_filing_type="10-K",
                    days_since_filing=42,
                    risk_flags=[],
                    risk_score=0.20,
                ),
                RiskGuardianReport(
                    ticker="META",
                    agent_name="RiskGuardian",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Moderate volatility",
                    beta=1.30,
                    annualized_volatility=0.30,
                    sharpe_ratio=1.1,
                    max_drawdown=-0.28,
                    suggested_position_size=0.06,
                    var_95=0.032,
                ),
            ],
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.40,
            expected_confidence_max=0.80,
            expected_min_grade="C",
        )
    )

    # 9. KO -- Consumer staple, defensive HOLD
    cases.append(
        BenchmarkCase(
            ticker="KO",
            description="Consumer staple, defensive HOLD",
            reports=[
                ValuationReport(
                    ticker="KO",
                    agent_name="ValuationScout",
                    signal="HOLD",
                    confidence=0.62,
                    reasoning="Fair value, low growth",
                    pe_ratio=25.0,
                    pb_ratio=10.0,
                    revenue_growth=0.02,
                    debt_to_equity=1.8,
                    fcf_yield=0.035,
                    intrinsic_value_gap=-0.03,
                ),
                MomentumReport(
                    ticker="KO",
                    agent_name="MomentumTracker",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Low momentum, stable",
                    rsi_14=47.0,
                    macd_signal=-0.1,
                    above_sma_50=False,
                    above_sma_200=True,
                    volume_trend="stable",
                    price_momentum_score=-0.05,
                ),
                PulseReport(
                    ticker="KO",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.55,
                    reasoning="Steady consumer staple news",
                    sentiment_score=0.02,
                    article_count=5,
                    top_headlines=["Coca-Cola international expansion"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="KO",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="Defensive regardless of regime",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="KO",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.72,
                    reasoning="Excellent compliance",
                    latest_filing_type="10-K",
                    days_since_filing=38,
                    risk_flags=[],
                    risk_score=0.05,
                ),
                RiskGuardianReport(
                    ticker="KO",
                    agent_name="RiskGuardian",
                    signal="BUY",
                    confidence=0.65,
                    reasoning="Very low beta, safe haven",
                    beta=0.55,
                    annualized_volatility=0.12,
                    sharpe_ratio=0.7,
                    max_drawdown=-0.10,
                    suggested_position_size=0.10,
                    var_95=0.013,
                ),
            ],
            expected_signals=["HOLD", "BUY"],
            expected_confidence_min=0.35,
            expected_confidence_max=0.75,
            expected_min_grade="C",
        )
    )

    # 10. GME -- Meme stock, high risk, low confidence
    cases.append(
        BenchmarkCase(
            ticker="GME",
            description="Meme stock, high risk, low confidence, SELL/HOLD",
            reports=[
                ValuationReport(
                    ticker="GME",
                    agent_name="ValuationScout",
                    signal="SELL",
                    confidence=0.65,
                    reasoning="Weak fundamentals, declining revenue",
                    pe_ratio=-15.0,
                    pb_ratio=2.5,
                    revenue_growth=-0.15,
                    debt_to_equity=0.2,
                    fcf_yield=-0.02,
                    intrinsic_value_gap=-0.40,
                ),
                MomentumReport(
                    ticker="GME",
                    agent_name="MomentumTracker",
                    signal="HOLD",
                    confidence=0.45,
                    reasoning="Volatile, no clear trend",
                    rsi_14=45.0,
                    macd_signal=-0.3,
                    above_sma_50=False,
                    above_sma_200=False,
                    volume_trend="decreasing",
                    price_momentum_score=-0.3,
                ),
                PulseReport(
                    ticker="GME",
                    agent_name="PulseMonitor",
                    signal="HOLD",
                    confidence=0.40,
                    reasoning="Meme activity fading",
                    sentiment_score=-0.10,
                    article_count=8,
                    top_headlines=["GameStop meme rally fades"],
                    event_flags=[],
                ),
                EconomyReport(
                    ticker="GME",
                    agent_name="EconomyWatcher",
                    signal="HOLD",
                    confidence=0.50,
                    reasoning="Macro neutral for retail",
                    gdp_growth=2.5,
                    inflation_rate=3.2,
                    fed_funds_rate=5.25,
                    unemployment_rate=3.8,
                    macro_regime="expansion",
                ),
                ComplianceReport(
                    ticker="GME",
                    agent_name="ComplianceChecker",
                    signal="HOLD",
                    confidence=0.60,
                    reasoning="No major flags",
                    latest_filing_type="10-K",
                    days_since_filing=70,
                    risk_flags=[],
                    risk_score=0.30,
                ),
                RiskGuardianReport(
                    ticker="GME",
                    agent_name="RiskGuardian",
                    signal="SELL",
                    confidence=0.55,
                    reasoning="Extreme volatility, meme risk",
                    beta=2.50,
                    annualized_volatility=0.80,
                    sharpe_ratio=-0.2,
                    max_drawdown=-0.70,
                    suggested_position_size=0.02,
                    var_95=0.085,
                ),
            ],
            expected_signals=["SELL", "HOLD"],
            expected_confidence_min=0.25,
            expected_confidence_max=0.70,
            expected_min_grade="D",
        )
    )

    return cases


BENCHMARK_SUITE: list[BenchmarkCase] = _make_benchmark_suite()

__all__ = [
    "BenchmarkCase",
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkSuiteResult",
    "BENCHMARK_SUITE",
    "GRADE_RANK",
]
