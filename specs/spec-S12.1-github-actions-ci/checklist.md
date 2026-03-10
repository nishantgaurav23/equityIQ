# Checklist -- Spec S12.1: GitHub Actions CI Pipeline

## Phase 1: Setup & Dependencies
- [x] Verify S1.2 (pyproject.toml) is implemented
- [x] Verify S11.1 (Dockerfile) is implemented
- [x] Create `.github/workflows/` directory
- [x] Add `pyyaml` to dev dependencies in pyproject.toml (for tests)

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_ci_workflow.py`
- [x] Write test: `test_ci_workflow_exists`
- [x] Write test: `test_ci_workflow_valid_yaml`
- [x] Write test: `test_ci_workflow_name`
- [x] Write test: `test_ci_trigger_push`
- [x] Write test: `test_ci_trigger_pull_request`
- [x] Write test: `test_ci_python_version`
- [x] Write test: `test_ci_pip_cache`
- [x] Write test: `test_ci_install_step`
- [x] Write test: `test_ci_pytest_step`
- [x] Write test: `test_ci_ruff_check_step`
- [x] Write test: `test_ci_ruff_format_step`
- [x] Write test: `test_ci_runs_on_ubuntu`
- [x] Write test: `test_ci_concurrency_group`
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Create `.github/workflows/ci.yml`
- [x] Configure workflow name and triggers (push + pull_request)
- [x] Configure concurrency group with cancel-in-progress
- [x] Set up job with `ubuntu-latest` runner
- [x] Add Python 3.12 setup step with pip caching
- [x] Add dependency install step
- [x] Add pytest step
- [x] Add ruff check step
- [x] Add ruff format check step
- [x] Run tests -- expect pass (Green)

## Phase 4: Integration
- [x] Validate YAML syntax with a linter or parser
- [x] Run `ruff check .` on any new Python files
- [x] Run full test suite: `python -m pytest tests/ -v --tb=short`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets in workflow
- [x] Workflow uses latest stable action versions (v4/v5)
- [x] Update roadmap.md status: pending -> done
