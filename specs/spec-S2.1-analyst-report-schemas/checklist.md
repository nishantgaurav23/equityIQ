# Checklist -- Spec S2.1: Analyst Report Schemas

## Phase 1: Setup & Dependencies
- [x] Verify S1.1 (dependency-declaration) is implemented -- pydantic available in pyproject.toml
- [x] Create `config/data_contracts.py` (or locate if exists)
- [x] Ensure `config/__init__.py` exists

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_data_contracts.py`
- [x] Write failing tests for AnalystReport (FR-1): valid creation, confidence clamping, default timestamp
- [x] Write failing tests for ValuationReport (FR-2): inheritance, nullable fields
- [x] Write failing tests for MomentumReport (FR-3): RSI clamping, momentum score clamping
- [x] Write failing tests for PulseReport (FR-4): sentiment clamping, confidence cap with low article count
- [x] Write failing tests for EconomyReport (FR-5): macro_regime literal validation
- [x] Write failing tests for ComplianceReport (FR-6): risk_score clamping
- [x] Write failing tests for RiskGuardianReport (FR-7): position size cap, volatility non-negative, drawdown non-positive
- [x] Write tests for serialization (model_dump) and signal literal validation
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement AnalystReport base model with field_validators -- pass its tests
- [x] Implement ValuationReport -- pass its tests
- [x] Implement MomentumReport with RSI/momentum clamping -- pass its tests
- [x] Implement PulseReport with sentiment clamping + confidence cap logic -- pass its tests
- [x] Implement EconomyReport with macro_regime literal -- pass its tests
- [x] Implement ComplianceReport with risk_score clamping -- pass its tests
- [x] Implement RiskGuardianReport with position size cap + volatility/drawdown clamping -- pass its tests
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure `config/data_contracts.py` is importable from project root
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked (8 outcomes)
- [x] No hardcoded secrets
- [x] Update roadmap.md status: `spec-written` -> `done`
