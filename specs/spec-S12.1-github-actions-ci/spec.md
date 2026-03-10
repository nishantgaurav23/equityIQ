# Spec S12.1 -- GitHub Actions CI Pipeline

## Overview
Continuous Integration pipeline using GitHub Actions. On every push and pull request, the workflow checks out code, sets up Python 3.12, installs dependencies from pyproject.toml, runs the full test suite (pytest), and runs the linter (ruff check + format). The pipeline fails fast on any error to provide rapid feedback.

## Dependencies
- **S1.2** (pyproject.toml) -- dependency declaration for install step
- **S11.1** (Dockerfile) -- confirms Docker multi-stage build exists (not directly used by CI, but validates project structure)

## Target Location
`.github/workflows/ci.yml`

---

## Functional Requirements

### FR-1: Trigger on Push and Pull Request
- **What**: The CI workflow triggers on every `push` to any branch and every `pull_request` targeting `main`
- **Inputs**: Git push event or PR event
- **Outputs**: Workflow run starts automatically
- **Edge cases**: Draft PRs should still trigger CI; closed PRs should not

### FR-2: Python 3.12 Environment Setup
- **What**: The workflow sets up Python 3.12 using `actions/setup-python@v5` with pip caching
- **Inputs**: Python version specification (`3.12`)
- **Outputs**: Python 3.12 available in PATH, pip cache restored if available
- **Edge cases**: Cache miss on first run (should still succeed, just slower)

### FR-3: Dependency Installation
- **What**: Install project dependencies from pyproject.toml including dev extras
- **Inputs**: `pyproject.toml` with `[project.optional-dependencies] dev`
- **Outputs**: All runtime + dev dependencies installed (pytest, ruff, pytest-asyncio, pytest-mock)
- **Edge cases**: Dependency resolution failure should fail the job immediately

### FR-4: Test Execution
- **What**: Run `python -m pytest tests/ -v --tb=short` and fail the workflow if any test fails
- **Inputs**: Test files in `tests/` directory
- **Outputs**: Test results with verbose output and short tracebacks; non-zero exit code on failure
- **Edge cases**: No tests found (should still pass with a warning); test timeout (default pytest timeout applies)

### FR-5: Lint Execution
- **What**: Run `ruff check .` and `ruff format --check .` to enforce code quality
- **Inputs**: All Python files in the repository
- **Outputs**: Lint results; non-zero exit code on lint violations or format issues
- **Edge cases**: ruff config from pyproject.toml must be respected (line-length: 100, select E/F/I)

### FR-6: Fail Fast Strategy
- **What**: Use `fail-fast: true` (default) so if any job step fails, subsequent steps are skipped
- **Inputs**: Step exit codes
- **Outputs**: Workflow marked as failed; clear indication of which step failed
- **Edge cases**: Multiple simultaneous failures in matrix builds (not applicable -- single job)

### FR-7: Concurrency Control
- **What**: Cancel in-progress CI runs when a new push arrives on the same branch/PR, to save CI minutes
- **Inputs**: Branch name or PR number
- **Outputs**: Previous run cancelled, new run proceeds
- **Edge cases**: Concurrent pushes to different branches should run independently

---

## Tangible Outcomes

- [ ] **Outcome 1**: `.github/workflows/ci.yml` exists and is valid YAML
- [ ] **Outcome 2**: Workflow triggers on `push` (all branches) and `pull_request` (to main)
- [ ] **Outcome 3**: Python 3.12 is set up with pip caching enabled
- [ ] **Outcome 4**: Dependencies install from `pip install ".[dev]"`
- [ ] **Outcome 5**: `pytest tests/ -v --tb=short` runs as a named step
- [ ] **Outcome 6**: `ruff check .` and `ruff format --check .` run as named steps
- [ ] **Outcome 7**: Concurrency group cancels stale runs per branch/PR
- [ ] **Outcome 8**: Workflow uses `ubuntu-latest` runner

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_ci_workflow_exists**: Verify `.github/workflows/ci.yml` file exists
2. **test_ci_workflow_valid_yaml**: Parse the file as YAML and confirm it's valid
3. **test_ci_workflow_name**: Workflow has a descriptive `name` field
4. **test_ci_trigger_push**: `on.push` trigger is configured
5. **test_ci_trigger_pull_request**: `on.pull_request` trigger targets `main`
6. **test_ci_python_version**: Job uses Python 3.12 via `actions/setup-python`
7. **test_ci_pip_cache**: `actions/setup-python` has `cache: 'pip'` configured
8. **test_ci_install_step**: A step runs `pip install ".[dev]"` or equivalent
9. **test_ci_pytest_step**: A step runs pytest with expected flags
10. **test_ci_ruff_check_step**: A step runs `ruff check .`
11. **test_ci_ruff_format_step**: A step runs `ruff format --check .`
12. **test_ci_runs_on_ubuntu**: Job runs on `ubuntu-latest`
13. **test_ci_concurrency_group**: Concurrency group is configured to cancel in-progress runs

### Mocking Strategy
- No external services to mock -- tests validate YAML structure by parsing the workflow file
- Use `yaml.safe_load()` to parse and assert on workflow structure

### Coverage Expectation
- All functional requirements covered by at least one structural test
- Tests validate YAML keys and values, not GitHub Actions runtime behavior

---

## References
- roadmap.md -- Phase 12: GCP Deployment
- design.md -- CI/CD architecture
- [GitHub Actions documentation](https://docs.github.com/en/actions)
- pyproject.toml -- dependency declaration
- Makefile -- local-test and local-lint targets (CI mirrors these)
