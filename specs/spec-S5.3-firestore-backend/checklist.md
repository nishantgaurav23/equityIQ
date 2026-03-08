# Checklist -- Spec S5.3: Firestore Backend

## Phase 1: Setup & Dependencies
- [x] Verify S5.1 (InsightVault) is implemented and tests pass
- [x] Add `google-cloud-firestore` to pyproject.toml
- [x] Create `memory/firestore_vault.py`

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_firestore_vault.py`
- [x] Write failing tests for initialize (FR-2)
- [x] Write failing tests for store_verdict (FR-3)
- [x] Write failing tests for get_verdict (FR-4)
- [x] Write failing tests for list_verdicts (FR-5)
- [x] Write failing tests for delete_verdict (FR-6)
- [x] Write failing tests for close (FR-7)
- [x] Write failing tests for get_vault factory (FR-8)
- [x] Run tests -- expect failures (Red) -- 16/16 failed

## Phase 3: Implementation
- [x] Implement FirestoreVault.__init__ and initialize() (FR-1, FR-2)
- [x] Implement store_verdict() (FR-3)
- [x] Implement get_verdict() (FR-4)
- [x] Implement list_verdicts() (FR-5)
- [x] Implement delete_verdict() (FR-6)
- [x] Implement close() (FR-7)
- [x] Implement get_vault() factory function (FR-8)
- [x] Run tests -- expect pass (Green) -- 16/16 passed
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure memory/__init__.py exports FirestoreVault and get_vault
- [x] Run make local-lint -- all checks passed
- [x] Run full test suite: make local-test -- 421/421 passed

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets (GCP_PROJECT_ID from settings)
- [x] All Firestore calls wrapped in try/except
- [x] Logging includes relevant context (session_id, ticker)
- [x] Update roadmap.md status: spec-written -> done
