# Checklist -- Spec S1.1: Dependency Declaration

## Phase 1: Setup & Dependencies
- [x] No dependencies to verify (this is the root spec)
- [x] Confirm project root directory structure exists

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_project_config.py
- [x] Write failing tests for FR-1 (pyproject.toml existence, validity, runtime deps)
- [x] Write failing tests for FR-2 (ruff config)
- [x] Write failing tests for FR-3 (pytest config)
- [x] Write failing tests for FR-4 (.env.example)
- [x] Write failing tests for FR-5 (.gitignore)
- [x] Run tests -- expect failures (Red) -- 8 failed, 3 passed

## Phase 3: Implementation
- [x] Create `pyproject.toml` with project metadata and runtime deps (FR-1)
- [x] Add `[project.optional-dependencies]` dev group (FR-1)
- [x] Add `[tool.ruff]` config (FR-2)
- [x] Add `[tool.pytest.ini_options]` config (FR-3)
- [x] `.env.example` already existed with all 9 variables and comments (FR-4)
- [x] `.env` already in `.gitignore` (FR-5)
- [x] Run tests -- 11/11 passed (Green)
- [x] No refactoring needed

## Phase 4: Integration
- [x] Run `pip install -e ".[dev]"` -- verified success (installs ruff, pytest-mock, equityiq)
- [x] Run `pip install -e ".[dev]"` -- dev deps installed
- [x] Run `ruff check .` -- config picked up, all checks passed
- [x] Run `pytest --co` -- test collection works, 11 tests collected

## Phase 5: Verification
- [x] All 6 tangible outcomes checked
- [x] No hardcoded secrets in any file
- [x] `.env.example` contains only placeholder values
- [x] Update roadmap.md status: spec-written -> done
