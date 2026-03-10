# Checklist -- Spec S14.3: Historical Backtesting

## Phase 1: Setup & Dependencies
- [x] Verify dependencies S14.2 and S5.2 are implemented
- [x] Create target file: evaluation/backtester.py
- [x] Create test file: tests/test_backtester.py

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_backtester.py
- [x] Write failing tests for BacktestConfig model (FR-1)
- [x] Write failing tests for BacktestResult model (FR-2)
- [x] Write failing tests for BacktestSummary model (FR-3)
- [x] Write failing tests for is_signal_correct() (FR-7)
- [x] Write failing tests for evaluate_verdict() (FR-4)
- [x] Write failing tests for run_backtest() (FR-5)
- [x] Write failing tests for run_multi_ticker() (FR-6)
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement BacktestConfig model (FR-1) -- pass model tests
- [x] Implement BacktestResult model (FR-2) -- pass model tests
- [x] Implement BacktestSummary model (FR-3) -- pass model tests
- [x] Implement is_signal_correct() (FR-7) -- pass correctness tests
- [x] Implement evaluate_verdict() (FR-4) -- pass evaluation tests
- [x] Implement run_backtest() (FR-5) -- pass backtest tests
- [x] Implement run_multi_ticker() (FR-6) -- pass multi-ticker tests
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure evaluation/__init__.py exports backtester classes
- [x] Run ruff lint check
- [x] Run full test suite

## Phase 5: Verification
- [x] All 7 tangible outcomes checked
- [x] No hardcoded secrets
- [x] All external calls wrapped in try/except
- [x] Update roadmap.md status: spec-written -> done
