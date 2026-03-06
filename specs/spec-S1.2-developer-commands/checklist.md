# Checklist -- Spec S1.2: Developer Commands

## Phase 1: Setup & Dependencies
- [x] Verify dependencies (none) are implemented
- [x] Create or locate target files (Makefile at project root)
- [x] Confirm pyproject.toml exists (S1.1 done)

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_makefile.py
- [x] Write failing tests for each FR (target existence, execution)
- [x] Run pytest -- expect failures (Red) -- 10 failed, 1 passed

## Phase 3: Implementation
- [x] Implement Makefile with all 8 targets
- [x] FR-1: venv target (python3.12 -m venv venv)
- [x] FR-2: install target (pip install .)
- [x] FR-3: install-dev target (pip install ".[dev]")
- [x] FR-4: local-dev target (uvicorn app:app --reload --port 8000)
- [x] FR-5: local-test target (python -m pytest tests/ -v --tb=short)
- [x] FR-6: local-lint target (ruff check . && ruff format --check .)
- [x] FR-7: dev target (docker compose up --build)
- [x] FR-8: test target (docker compose run --rm app pytest)
- [x] Add .PHONY declarations for all targets
- [x] Run tests -- expect pass (Green) -- 11/11 passed
- [x] Refactor if needed (fixed lint warning)

## Phase 4: Integration
- [x] Verify Makefile works from project root
- [x] Run make local-lint
- [x] Run full test suite: make local-test -- 22/22 passed

## Phase 5: Verification
- [x] All tangible outcomes checked (5/5 PASS)
- [x] No hardcoded secrets
- [x] Logging includes request_id where applicable -- N/A for Makefile
- [x] Update roadmap.md status: spec-written -> done
