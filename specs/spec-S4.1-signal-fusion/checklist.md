# Checklist -- Spec S4.1: Signal Fusion (XGBoost Signal Synthesis)

## Phase 1: Setup & Dependencies
- [x] Verify S2.1 (AnalystReport schemas) is implemented and tests pass
- [x] Verify S2.2 (FinalVerdict schema) is implemented and tests pass
- [x] Create `models/` directory with `__init__.py`
- [x] Create `models/signal_fusion.py`
- [x] Confirm xgboost + scikit-learn already in pyproject.toml

## Phase 2: Tests First (TDD)
- [x] Create `tests/test_signal_fusion.py`
- [x] Write tests for signal_to_numeric / numeric_to_signal (FR-2)
- [x] Write tests for extract_features (FR-1)
- [x] Write tests for weighted_average_predict (FR-3)
- [x] Write tests for fit (FR-4)
- [x] Write tests for predict (FR-5)
- [x] Write tests for compliance override (FR-6)
- [x] Write tests for strong signal threshold enforcement
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement signal_to_numeric / numeric_to_signal (FR-2)
- [x] Implement extract_features (FR-1)
- [x] Implement weighted_average_predict (FR-3)
- [x] Implement SignalFusionModel class with __init__ (FR-7)
- [x] Implement fit (FR-4)
- [x] Implement predict (FR-5)
- [x] Implement apply_compliance_override (FR-6)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Add models/ exports to `models/__init__.py`
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All 8 tangible outcomes checked
- [x] No hardcoded secrets
- [x] Position size cap not relevant here (that's RiskGuardian)
- [x] Compliance override tested for going_concern and restatement
- [x] STRONG_BUY/STRONG_SELL threshold (0.75) enforced
- [x] Update roadmap.md status: spec-written -> done
