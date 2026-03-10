# Checklist -- Spec S14.4: End-to-End Smoke Test

## Phase 1: Setup & Dependencies
- [x] Verify S10.1 (Pipeline Wiring) is implemented and tests pass
- [x] Create target file: tests/test_e2e.py
- [x] No new dependencies needed (uses existing pytest, FastAPI TestClient)

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_e2e.py
- [x] Write test_health_endpoint_returns_ok
- [x] Write test_full_aapl_analysis_returns_verdict
- [x] Write test_response_time_under_30s
- [x] Write test_all_agent_signals_present
- [x] Write test_agent_details_populated
- [x] Write test_verdict_confidence_in_range
- [x] Write test_verdict_has_session_id
- [x] Write test_verdict_stored_in_vault
- [x] Write test_compliance_going_concern_forces_sell
- [x] Write test_portfolio_smoke
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Tests are the implementation (this is a test-only spec)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify tests run as part of full test suite
- [x] Run ruff lint on test file
- [x] Run full test suite: python -m pytest tests/test_e2e.py -v

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets in tests
- [x] All FRs covered by at least one test
- [x] Update roadmap.md status: spec-written -> done
