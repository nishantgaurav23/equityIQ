# Checklist -- Spec S14.2: Benchmark Test Cases

## Phase 1: Setup & Dependencies
- [x] Verify S14.1 (Quality Assessor) is implemented and tests pass
- [x] Create `evaluation/benchmarks/` directory with `__init__.py`
- [x] Review `models/signal_fusion.py` for synthesizer interface

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_benchmarks.py`
- [x] Write failing tests for FR-1 (BenchmarkCase model)
- [x] Write failing tests for FR-2 (BENCHMARK_SUITE, 10 cases)
- [x] Write failing tests for FR-3 (BenchmarkRunner)
- [x] Write failing tests for FR-4 (signal range validation)
- [x] Write failing tests for FR-5 (confidence range validation)
- [x] Write failing tests for FR-6 (quality grade validation)
- [x] Run `python -m pytest tests/test_benchmarks.py -v` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement `BenchmarkCase` model (FR-1)
- [x] Implement `BenchmarkResult` and `BenchmarkSuiteResult` models
- [x] Implement 10 benchmark cases in `BENCHMARK_SUITE` (FR-2)
- [x] Implement `BenchmarkRunner.run_case()` (FR-3)
- [x] Implement signal range validation (FR-4)
- [x] Implement confidence range validation (FR-5)
- [x] Implement quality grade validation (FR-6)
- [x] Implement `BenchmarkRunner.run_suite()` (FR-3)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Export public API from `evaluation/benchmarks/__init__.py`
- [x] Run `ruff check evaluation/ tests/test_benchmarks.py`
- [x] Run full test suite: `python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] All 10 benchmark cases pass
- [x] Update roadmap.md status: pending -> done
