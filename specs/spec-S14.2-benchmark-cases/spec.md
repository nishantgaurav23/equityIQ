# Spec S14.2 -- Benchmark Test Cases

## Overview
Benchmark test cases for 10 well-known stocks with expected signal ranges. Each benchmark defines a stock (e.g., AAPL, TSLA, JPM) with realistic mock agent data and expected signal/confidence ranges. The benchmark runner validates that the full pipeline (agents -> SignalSynthesizer -> FinalVerdict) produces reasonable outputs within defined bounds. This ensures the system doesn't produce wildly incorrect results for well-understood stocks.

## Dependencies
- S14.1 (Quality Assessor) -- used to grade benchmark verdicts

## Target Location
- `evaluation/benchmarks/` -- benchmark definitions and runner
- `tests/test_benchmarks.py` -- test suite

---

## Functional Requirements

### FR-1: Benchmark Case Definition
- **What**: Define a `BenchmarkCase` Pydantic model that specifies a stock ticker, mock agent reports (all 6 agents), and expected outcome ranges.
- **Inputs**: Ticker, mock `AnalystReport` variants for each agent, expected `final_signal` options (list of acceptable signals), expected confidence range (min, max), expected quality grade range.
- **Outputs**: `BenchmarkCase` model with all fields validated.
- **Edge cases**: Ensure at least one expected signal is provided; confidence range must be 0-1.

### FR-2: Benchmark Suite (10 Stocks)
- **What**: Provide a suite of 10 benchmark cases covering diverse stock profiles:
  1. **AAPL** -- Large-cap tech, typically BUY/HOLD, high confidence
  2. **TSLA** -- High-volatility growth, mixed signals, moderate confidence
  3. **JPM** -- Blue-chip financials, stable HOLD/BUY
  4. **AMZN** -- Large-cap tech/retail, growth-oriented BUY
  5. **JNJ** -- Defensive healthcare, conservative HOLD/BUY
  6. **NVDA** -- AI/semiconductor momentum, BUY with high momentum
  7. **XOM** -- Energy/cyclical, macro-sensitive
  8. **META** -- Large-cap tech, sentiment-driven
  9. **KO** -- Consumer staple, defensive HOLD
  10. **GME** -- Meme stock, high risk, low confidence, SELL/HOLD
- **Inputs**: Each case has 6 agent reports with realistic metrics
- **Outputs**: `BENCHMARK_SUITE` list of `BenchmarkCase` instances
- **Edge cases**: Each benchmark must have all 6 agent signals populated

### FR-3: Benchmark Runner
- **What**: A `BenchmarkRunner` class that executes benchmark cases by feeding mock agent data through `SignalSynthesizer` and `QualityAssessor`, then validates outcomes against expected ranges.
- **Inputs**: A `BenchmarkCase` or list of cases
- **Outputs**: `BenchmarkResult` per case (pass/fail, actual signal, actual confidence, actual grade, deviations). `BenchmarkSuiteResult` for full suite (total, passed, failed, pass_rate, results list).
- **Edge cases**: If synthesizer raises an exception, mark the case as failed with error message.

### FR-4: Signal Range Validation
- **What**: Check that the produced `final_signal` is within the benchmark's list of acceptable signals.
- **Inputs**: Actual signal, list of expected signals
- **Outputs**: Boolean pass/fail
- **Edge cases**: If expected list has only one signal, exact match required.

### FR-5: Confidence Range Validation
- **What**: Check that `overall_confidence` falls within the benchmark's expected min/max range.
- **Inputs**: Actual confidence, expected (min, max) tuple
- **Outputs**: Boolean pass/fail
- **Edge cases**: Boundary values (exact min/max) should pass.

### FR-6: Quality Grade Validation
- **What**: Run `QualityAssessor.assess()` on the verdict and check the grade meets minimum expectation.
- **Inputs**: FinalVerdict, minimum expected grade (e.g., "C")
- **Outputs**: Boolean pass/fail
- **Edge cases**: Grade comparison uses ordinal ranking (A > B > C > D > F).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `evaluation/benchmarks/__init__.py` exports `BenchmarkCase`, `BenchmarkRunner`, `BENCHMARK_SUITE`
- [ ] **Outcome 2**: `BENCHMARK_SUITE` contains exactly 10 benchmark cases (AAPL, TSLA, JPM, AMZN, JNJ, NVDA, XOM, META, KO, GME)
- [ ] **Outcome 3**: `BenchmarkRunner.run_suite()` returns `BenchmarkSuiteResult` with pass/fail for each case
- [ ] **Outcome 4**: All 10 benchmark cases pass when run against the synthesizer with their mock data
- [ ] **Outcome 5**: `QualityAssessor` grade validation integrated into each benchmark result
- [ ] **Outcome 6**: Test file `tests/test_benchmarks.py` covers all FRs with at least 10 tests

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_benchmark_case_model_valid**: BenchmarkCase accepts valid data
2. **test_benchmark_case_requires_expected_signals**: Validates at least one expected signal
3. **test_benchmark_case_confidence_range_clamped**: min/max confidence clamped to [0,1]
4. **test_benchmark_suite_has_10_cases**: BENCHMARK_SUITE has exactly 10 entries
5. **test_benchmark_suite_unique_tickers**: All 10 tickers are unique
6. **test_benchmark_suite_all_agents_present**: Each case has all 6 agent signals
7. **test_benchmark_runner_single_case**: Runner produces BenchmarkResult for one case
8. **test_benchmark_runner_signal_validation**: Signal within expected range -> pass
9. **test_benchmark_runner_signal_out_of_range**: Signal outside expected -> fail
10. **test_benchmark_runner_confidence_validation**: Confidence within range -> pass
11. **test_benchmark_runner_confidence_out_of_range**: Below min or above max -> fail
12. **test_benchmark_runner_quality_grade_check**: Grade meets minimum -> pass
13. **test_benchmark_runner_full_suite**: run_suite returns BenchmarkSuiteResult with all 10 results
14. **test_benchmark_runner_all_pass**: All 10 benchmarks pass with their mock data
15. **test_benchmark_runner_handles_exception**: Synthesizer error -> failed result, no crash

### Mocking Strategy
- `SignalSynthesizer.synthesize()` is called with mock agent reports -- use real synthesizer logic (weighted average fallback) since mock data is deterministic
- `QualityAssessor.assess()` is called on the resulting verdict -- use real implementation
- No external API calls needed (all data is mock)

### Coverage Expectation
- All public functions and classes have tests
- Each of the 10 benchmark cases validated individually
- Edge cases: empty signals, out-of-range confidence, grade boundaries

---

## References
- roadmap.md -- S14.2 spec definition
- evaluation/quality_assessor.py -- QualityAssessor (S14.1)
- models/signal_fusion.py -- SignalSynthesizer
- config/data_contracts.py -- FinalVerdict, AnalystReport variants
