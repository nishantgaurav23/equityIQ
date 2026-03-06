# Checklist -- Spec S2.2: Verdict Schemas

## Phase 1: Setup & Dependencies
- [x] Verify S2.1 (analyst-report-schemas) is implemented -- AnalystReport exists in data_contracts.py
- [x] Confirm `config/data_contracts.py` exists and is importable

## Phase 2: Tests First (TDD)
- [x] Add verdict tests to `tests/test_data_contracts.py`
- [x] Write failing tests for FinalVerdict (FR-1): valid creation, confidence clamping, STRONG signal downgrade
- [x] Write failing tests for PortfolioInsight (FR-2): valid creation, diversification clamping
- [x] Write tests for serialization and signal literal validation
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement FinalVerdict model with field_validator + model_validator -- pass its tests
- [x] Implement PortfolioInsight model with field_validator -- pass its tests
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure FinalVerdict and PortfolioInsight are importable from config.data_contracts
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked (9 outcomes)
- [x] No hardcoded secrets
- [x] Update roadmap.md status: `spec-written` -> `done`
