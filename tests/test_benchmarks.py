"""Tests for evaluation/benchmarks -- S14.2 Benchmark Test Cases."""

import pytest

from evaluation.benchmarks import (
    BENCHMARK_SUITE,
    GRADE_RANK,
    BenchmarkCase,
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSuiteResult,
)

# ---------------------------------------------------------------------------
# FR-1: BenchmarkCase model
# ---------------------------------------------------------------------------


class TestBenchmarkCaseModel:
    def test_benchmark_case_model_valid(self):
        """BenchmarkCase accepts valid data with all required fields."""
        from config.data_contracts import (
            ComplianceReport,
            EconomyReport,
            MomentumReport,
            PulseReport,
            RiskGuardianReport,
            ValuationReport,
        )

        reports = [
            ValuationReport(
                ticker="AAPL", agent_name="ValuationScout",
                signal="BUY", confidence=0.7, reasoning="test",
            ),
            MomentumReport(
                ticker="AAPL", agent_name="MomentumTracker",
                signal="BUY", confidence=0.7, reasoning="test",
            ),
            PulseReport(
                ticker="AAPL", agent_name="PulseMonitor",
                signal="BUY", confidence=0.7, reasoning="test", article_count=5,
            ),
            EconomyReport(
                ticker="AAPL", agent_name="EconomyWatcher",
                signal="HOLD", confidence=0.6, reasoning="test",
            ),
            ComplianceReport(
                ticker="AAPL", agent_name="ComplianceChecker",
                signal="HOLD", confidence=0.7, reasoning="test",
            ),
            RiskGuardianReport(
                ticker="AAPL", agent_name="RiskGuardian",
                signal="HOLD", confidence=0.6, reasoning="test",
            ),
        ]

        case = BenchmarkCase(
            ticker="AAPL",
            description="Large-cap tech",
            reports=reports,
            expected_signals=["BUY", "HOLD"],
            expected_confidence_min=0.4,
            expected_confidence_max=0.8,
            expected_min_grade="C",
        )
        assert case.ticker == "AAPL"
        assert len(case.reports) == 6
        assert case.expected_signals == ["BUY", "HOLD"]

    def test_benchmark_case_requires_expected_signals(self):
        """BenchmarkCase must have at least one expected signal."""
        from config.data_contracts import ValuationReport

        reports = [
            ValuationReport(
                ticker="TEST", agent_name="ValuationScout",
                signal="BUY", confidence=0.7, reasoning="test",
            ),
        ]
        with pytest.raises(ValueError, match="at least one expected signal"):
            BenchmarkCase(
                ticker="TEST",
                description="test",
                reports=reports,
                expected_signals=[],
                expected_confidence_min=0.3,
                expected_confidence_max=0.8,
                expected_min_grade="C",
            )

    def test_benchmark_case_confidence_range_clamped(self):
        """Confidence min/max clamped to [0, 1]."""
        from config.data_contracts import ValuationReport

        reports = [
            ValuationReport(
                ticker="TEST", agent_name="ValuationScout",
                signal="BUY", confidence=0.7, reasoning="test",
            ),
        ]
        case = BenchmarkCase(
            ticker="TEST",
            description="test",
            reports=reports,
            expected_signals=["BUY"],
            expected_confidence_min=-0.5,
            expected_confidence_max=1.5,
            expected_min_grade="F",
        )
        assert case.expected_confidence_min == 0.0
        assert case.expected_confidence_max == 1.0


# ---------------------------------------------------------------------------
# FR-2: Benchmark Suite (10 stocks)
# ---------------------------------------------------------------------------


class TestBenchmarkSuite:
    def test_benchmark_suite_has_10_cases(self):
        """BENCHMARK_SUITE contains exactly 10 entries."""
        assert len(BENCHMARK_SUITE) == 10

    def test_benchmark_suite_unique_tickers(self):
        """All 10 tickers are unique."""
        tickers = [c.ticker for c in BENCHMARK_SUITE]
        assert len(set(tickers)) == 10

    def test_benchmark_suite_expected_tickers(self):
        """Suite includes the expected well-known tickers."""
        tickers = {c.ticker for c in BENCHMARK_SUITE}
        expected = {"AAPL", "TSLA", "JPM", "AMZN", "JNJ", "NVDA", "XOM", "META", "KO", "GME"}
        assert tickers == expected

    def test_benchmark_suite_all_agents_present(self):
        """Each case has all 6 agent reports."""
        for case in BENCHMARK_SUITE:
            agent_names = {r.agent_name for r in case.reports}
            assert "ValuationScout" in agent_names, f"{case.ticker}: missing ValuationScout"
            assert "MomentumTracker" in agent_names, f"{case.ticker}: missing MomentumTracker"
            assert "PulseMonitor" in agent_names, f"{case.ticker}: missing PulseMonitor"
            assert "EconomyWatcher" in agent_names, f"{case.ticker}: missing EconomyWatcher"
            assert "ComplianceChecker" in agent_names, f"{case.ticker}: missing ComplianceChecker"
            assert "RiskGuardian" in agent_names, f"{case.ticker}: missing RiskGuardian"

    def test_benchmark_suite_valid_confidence_ranges(self):
        """All cases have valid confidence ranges (min <= max)."""
        for case in BENCHMARK_SUITE:
            assert case.expected_confidence_min <= case.expected_confidence_max, (
                f"{case.ticker}: min > max confidence"
            )

    def test_benchmark_suite_valid_expected_signals(self):
        """All expected signals are valid 5-level signals."""
        valid_signals = {"STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"}
        for case in BENCHMARK_SUITE:
            for sig in case.expected_signals:
                assert sig in valid_signals, f"{case.ticker}: invalid signal {sig}"


# ---------------------------------------------------------------------------
# FR-3: Benchmark Runner
# ---------------------------------------------------------------------------


class TestBenchmarkRunner:
    def test_benchmark_runner_single_case(self):
        """Runner produces BenchmarkResult for one case."""
        runner = BenchmarkRunner()
        case = BENCHMARK_SUITE[0]  # AAPL
        result = runner.run_case(case)
        assert isinstance(result, BenchmarkResult)
        assert result.ticker == case.ticker
        assert result.actual_signal is not None
        assert result.actual_confidence is not None

    def test_benchmark_runner_full_suite(self):
        """run_suite returns BenchmarkSuiteResult with all 10 results."""
        runner = BenchmarkRunner()
        suite_result = runner.run_suite(BENCHMARK_SUITE)
        assert isinstance(suite_result, BenchmarkSuiteResult)
        assert suite_result.total == 10
        assert len(suite_result.results) == 10
        assert suite_result.passed + suite_result.failed == suite_result.total

    def test_benchmark_runner_all_pass(self):
        """All 10 benchmarks pass with their mock data."""
        runner = BenchmarkRunner()
        suite_result = runner.run_suite(BENCHMARK_SUITE)
        for r in suite_result.results:
            assert r.passed, (
                f"{r.ticker} FAILED: signal={r.actual_signal} "
                f"(expected {r.expected_signals}), "
                f"conf={r.actual_confidence:.2f} "
                f"(expected {r.expected_confidence_range}), "
                f"grade={r.actual_grade} "
                f"(min {r.expected_min_grade}), "
                f"issues={r.issues}"
            )
        assert suite_result.pass_rate == 1.0


# ---------------------------------------------------------------------------
# FR-4: Signal range validation
# ---------------------------------------------------------------------------


class TestSignalValidation:
    def test_signal_within_range_passes(self):
        """Signal present in expected list -> pass."""
        runner = BenchmarkRunner()
        assert runner._validate_signal("BUY", ["BUY", "HOLD"]) is True

    def test_signal_out_of_range_fails(self):
        """Signal not in expected list -> fail."""
        runner = BenchmarkRunner()
        assert runner._validate_signal("SELL", ["BUY", "HOLD"]) is False

    def test_signal_exact_match(self):
        """Single expected signal requires exact match."""
        runner = BenchmarkRunner()
        assert runner._validate_signal("BUY", ["BUY"]) is True
        assert runner._validate_signal("HOLD", ["BUY"]) is False


# ---------------------------------------------------------------------------
# FR-5: Confidence range validation
# ---------------------------------------------------------------------------


class TestConfidenceValidation:
    def test_confidence_within_range_passes(self):
        """Confidence within [min, max] -> pass."""
        runner = BenchmarkRunner()
        assert runner._validate_confidence(0.65, 0.4, 0.8) is True

    def test_confidence_below_min_fails(self):
        """Confidence below min -> fail."""
        runner = BenchmarkRunner()
        assert runner._validate_confidence(0.2, 0.4, 0.8) is False

    def test_confidence_above_max_fails(self):
        """Confidence above max -> fail."""
        runner = BenchmarkRunner()
        assert runner._validate_confidence(0.9, 0.4, 0.8) is False

    def test_confidence_at_boundaries_passes(self):
        """Exact min and max values should pass."""
        runner = BenchmarkRunner()
        assert runner._validate_confidence(0.4, 0.4, 0.8) is True
        assert runner._validate_confidence(0.8, 0.4, 0.8) is True


# ---------------------------------------------------------------------------
# FR-6: Quality grade validation
# ---------------------------------------------------------------------------


class TestGradeValidation:
    def test_grade_meets_minimum_passes(self):
        """Grade at or above minimum -> pass."""
        runner = BenchmarkRunner()
        assert runner._validate_grade("A", "C") is True
        assert runner._validate_grade("B", "B") is True
        assert runner._validate_grade("C", "C") is True

    def test_grade_below_minimum_fails(self):
        """Grade below minimum -> fail."""
        runner = BenchmarkRunner()
        assert runner._validate_grade("D", "C") is False
        assert runner._validate_grade("F", "B") is False

    def test_grade_rank_ordering(self):
        """Grade ranks: A > B > C > D > F."""
        assert GRADE_RANK["A"] > GRADE_RANK["B"]
        assert GRADE_RANK["B"] > GRADE_RANK["C"]
        assert GRADE_RANK["C"] > GRADE_RANK["D"]
        assert GRADE_RANK["D"] > GRADE_RANK["F"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_benchmark_runner_handles_exception(self):
        """Synthesizer error -> failed result, no crash."""
        runner = BenchmarkRunner()
        # Create a case with empty reports (would cause issues)
        case = BenchmarkCase(
            ticker="FAIL",
            description="intentional failure",
            reports=[],
            expected_signals=["BUY"],
            expected_confidence_min=0.5,
            expected_confidence_max=0.9,
            expected_min_grade="A",
        )
        result = runner.run_case(case)
        assert isinstance(result, BenchmarkResult)
        assert result.passed is False

    def test_benchmark_result_model(self):
        """BenchmarkResult stores all expected fields."""
        result = BenchmarkResult(
            ticker="TEST",
            passed=True,
            actual_signal="BUY",
            actual_confidence=0.65,
            actual_grade="B",
            expected_signals=["BUY", "HOLD"],
            expected_confidence_range=(0.4, 0.8),
            expected_min_grade="C",
            issues=[],
        )
        assert result.passed is True
        assert result.actual_signal == "BUY"

    def test_suite_result_pass_rate(self):
        """Pass rate calculated correctly."""
        suite = BenchmarkSuiteResult(
            total=4,
            passed=3,
            failed=1,
            pass_rate=0.75,
            results=[],
        )
        assert suite.pass_rate == 0.75
