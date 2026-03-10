# Checklist -- Spec S8.1: Signal Synthesizer Agent

## Phase 1: Setup & Dependencies
- [x] Verify S6.1 (BaseAnalystAgent) is implemented and tests pass
- [x] Verify S4.1 (SignalFusionModel) is implemented and tests pass
- [x] Verify S2.2 (FinalVerdict, RiskGuardianReport schemas) is implemented and tests pass
- [x] Create `agents/signal_synthesizer.py`
- [x] Create `tests/test_signal_synthesizer.py`

## Phase 2: Tests First (TDD)
- [x] Write test_signal_synthesizer_construction
- [x] Write test_synthesize_all_reports_buy
- [x] Write test_synthesize_all_reports_sell
- [x] Write test_synthesize_mixed_reports
- [x] Write test_synthesize_empty_reports
- [x] Write test_compliance_override_going_concern
- [x] Write test_compliance_override_restatement
- [x] Write test_compliance_override_no_flags
- [x] Write test_risk_summary_integration
- [x] Write test_risk_summary_none
- [x] Write test_weight_adjustment_contraction
- [x] Write test_weight_adjustment_stagflation
- [x] Write test_weight_adjustment_expansion
- [x] Write test_synthesize_missing_agents
- [x] Write test_synthesize_error_handling
- [x] Write test_factory_function
- [x] Write test_module_singleton
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement SignalSynthesizer class extending BaseAnalystAgent (FR-1)
- [x] Implement synthesize_signals tool function (FR-2)
- [x] Implement synthesize() direct method (FR-3)
- [x] Implement risk summary integration (FR-4)
- [x] Implement weight adjustment for macro regime (FR-5)
- [x] Compliance override delegation (FR-6, via SignalFusionModel)
- [x] Factory function and module singleton (FR-7)
- [x] Error handling in all paths (FR-8)
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify agent card generation works
- [x] Run ruff lint check
- [x] Run full test suite

## Phase 5: Verification
- [x] All 8 tangible outcomes checked
- [x] No hardcoded secrets
- [x] Logging includes agent_name context
- [x] Update roadmap.md status: spec-written -> done
