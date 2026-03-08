# Checklist -- Spec S7.5: Compliance Checker

## Phase 1: Setup & Dependencies
- [x] Verify S6.1 (BaseAnalystAgent) is implemented and tests pass
- [x] Verify S3.4 (SecConnector) is implemented and tests pass
- [x] Locate target file: agents/compliance_checker.py
- [x] Confirm ComplianceReport exists in config/data_contracts.py
- [x] Confirm "compliance_checker" persona exists in config/analyst_personas.py

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_compliance_checker.py
- [x] Write failing tests for tool functions (FR-1)
- [x] Write failing tests for agent class (FR-2)
- [x] Write failing tests for factory/exports (FR-3)
- [x] Write failing tests for analyze success + fallback
- [x] Write failing tests for agent card (FR-5)
- [x] Write tests for ComplianceReport schema validation
- [x] Run pytest -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement get_sec_filings_tool() -- wraps SecConnector.get_sec_filings()
- [x] Implement score_risk_tool() -- wraps SecConnector.score_risk()
- [x] Implement ComplianceCheckerAgent class extending BaseAnalystAgent
- [x] Implement create_compliance_checker() factory function
- [x] Add module-level compliance_checker instance
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify agent imports work from project root
- [x] Run ruff check agents/compliance_checker.py
- [x] Run full test suite: python -m pytest tests/ -v --tb=short

## Phase 5: Verification
- [x] All 12 tangible outcomes checked
- [x] No hardcoded secrets
- [x] All external calls wrapped in try/except
- [x] Tool functions return {} on error, never raise
- [x] Update roadmap.md status: spec-written -> done
