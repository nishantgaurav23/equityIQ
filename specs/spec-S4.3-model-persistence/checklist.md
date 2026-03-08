# Checklist -- Spec S4.3: Model Persistence

## Phase 1: Setup & Dependencies
- [x] Verify S4.1 (signal_fusion.py) is implemented and tests pass
- [x] Create target file: models/model_store.py
- [x] Add joblib to pyproject.toml

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_model_store.py
- [x] Write failing tests for FR-1 (save_model)
- [x] Write failing tests for FR-2 (load_model)
- [x] Write failing tests for FR-3 (list_models)
- [x] Write failing tests for FR-4 (delete_model)
- [x] Write failing tests for FR-5 (get_latest_model_path)
- [x] Write failing tests for FR-6 (ModelInfo dataclass)
- [x] Write failing tests for FR-7 (round-trip integrity)
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement ModelInfo dataclass
- [x] Implement ModelStore.__init__() with configurable base_dir
- [x] Implement FR-1 save() -- joblib.dump + timestamp naming
- [x] Implement FR-2 load() -- joblib.load + latest fallback
- [x] Implement FR-3 list() -- glob + parse filenames
- [x] Implement FR-4 delete() -- os.remove with safety checks
- [x] Implement FR-5 get_latest_path()
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] models/__init__.py exists (no explicit exports needed)
- [x] Run make local-lint -- PASS
- [x] Run full test suite: make local-test -- 332 passed

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] Logging on save/load/delete operations
- [x] Update roadmap.md status: spec-written -> done
