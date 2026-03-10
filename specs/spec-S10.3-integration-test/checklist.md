# Checklist -- Spec S10.3: Integration Test: Full Pipeline

## Phase 1: Setup & Dependencies
- [x] Verify S10.1 (Pipeline Wiring) is implemented and tests pass
- [x] Verify S10.2 (Graceful Degradation) is implemented and tests pass
- [x] Create target file: `tests/test_pipeline.py`
- [x] Verify FastAPI TestClient / httpx async test setup works

## Phase 2: Tests First (TDD)
- [x] Write test fixtures: mock agent reports (Valuation, Momentum, Pulse, Economy, Compliance, RiskGuardian)
- [x] Write `test_analyze_single_ticker_returns_valid_verdict`
- [x] Write `test_all_agents_called_during_analysis`
- [x] Write `test_verdict_stored_in_vault`
- [x] Write `test_session_id_consistency`
- [x] Write `test_portfolio_analysis_returns_valid_insight`
- [x] Write `test_portfolio_all_tickers_analyzed`
- [x] Write `test_graceful_degradation_single_agent_failure`
- [x] Write `test_graceful_degradation_warning_in_key_drivers`
- [x] Write `test_invalid_ticker_returns_error`
- [x] Write `test_empty_portfolio_returns_error`
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] All tests should pass with proper mocking (no production code to write -- this is a test-only spec)
- [x] Run tests -- expect pass (Green)
- [x] Refactor test helpers if needed

## Phase 4: Integration
- [x] Run `make local-lint` -- fix any ruff issues
- [x] Run full test suite: `make local-test` -- all tests pass (731 passed)

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets in tests
- [x] All external services are mocked (no real API calls)
- [x] Update roadmap.md status: spec-written -> done
