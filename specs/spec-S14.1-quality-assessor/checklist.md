# Checklist -- Spec S14.1: Quality Assessor

## Phase 1: Setup & Dependencies
- [x] Verify S10.1 (pipeline wiring) is implemented and tests pass
- [x] Create `evaluation/` directory and `evaluation/__init__.py`
- [x] Create target file: `evaluation/quality_assessor.py`

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_quality_assessor.py`
- [x] Write helper to build test FinalVerdict instances
- [x] Write failing tests for FR-1 (completeness scoring)
- [x] Write failing tests for FR-2 (consensus scoring)
- [x] Write failing tests for FR-3 (calibration scoring)
- [x] Write failing tests for FR-4 (overall grade)
- [x] Write failing tests for FR-5 (issue detection)
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Define `QualityAssessment` Pydantic model (scores, grade, issues)
- [x] Implement `QualityAssessor` class
- [x] Implement `_score_completeness()` -- FR-1
- [x] Implement `_score_consensus()` -- FR-2
- [x] Implement `_score_calibration()` -- FR-3
- [x] Implement `_compute_grade()` -- FR-4 (weighted average + letter grade)
- [x] Implement `_detect_issues()` -- FR-5
- [x] Implement `assess(verdict: FinalVerdict) -> QualityAssessment` -- orchestrates all
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure `evaluation/quality_assessor.py` is importable from project root
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] All scores clamped to [0.0, 1.0]
- [x] Grade always one of A/B/C/D/F
- [x] Issues list provides actionable descriptions
- [x] Update roadmap.md status: pending -> done (when ready)
