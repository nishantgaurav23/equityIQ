# Checklist -- Spec S4.2: Risk Calculator

## Phase 1: Setup & Dependencies
- [x] Verify S2.1 (analyst-report-schemas) is implemented and tests pass
- [x] Create `models/risk_calculator.py`
- [x] Confirm numpy is in pyproject.toml (already present via S1.1)

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_risk_calculator.py`
- [x] Write failing tests for calc_beta (normal + edge cases)
- [x] Write failing tests for calc_sharpe (normal + edge cases)
- [x] Write failing tests for calc_var_95 (normal + edge cases)
- [x] Write failing tests for calc_max_drawdown (normal + edge cases)
- [x] Write failing tests for calc_position_size (normal + cap + edge cases)
- [x] Write failing tests for calc_annualized_volatility (normal + edge cases)
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement calc_beta() -- covariance / variance with edge guards
- [x] Implement calc_sharpe() -- annualized Sharpe ratio
- [x] Implement calc_var_95() -- 5th percentile historical VaR
- [x] Implement calc_max_drawdown() -- peak-to-trough from price series
- [x] Implement calc_position_size() -- volatility-targeted sizing, capped at 0.10
- [x] Implement calc_annualized_volatility() -- std * sqrt(252)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure `models/__init__.py` exists for package imports
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] All functions are pure (no side effects, no API calls)
- [x] Position size never exceeds 0.10
- [x] Update roadmap.md status: spec-written -> done
