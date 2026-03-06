# Spec S1.2 -- Developer Commands

## Overview
Makefile providing standardized developer commands for virtual environment setup, dependency installation, local development server, testing, linting, and Docker workflows. Single entry point for all common development tasks.

## Dependencies
None (S1.1 pyproject.toml must exist but is already `done`)

## Target Location
`Makefile`

---

## Functional Requirements

### FR-1: Virtual environment creation
- **What**: `make venv` creates a Python 3.12 virtual environment at project root
- **Inputs**: None
- **Outputs**: `venv/` directory with Python 3.12 interpreter
- **Edge cases**: venv already exists (should recreate or skip gracefully)

### FR-2: Runtime dependency installation
- **What**: `make install` installs runtime dependencies from pyproject.toml into the venv
- **Inputs**: Active venv, pyproject.toml
- **Outputs**: All runtime packages installed
- **Edge cases**: venv not created yet (should depend on venv target)

### FR-3: Dev dependency installation
- **What**: `make install-dev` installs runtime + dev dependencies (pytest, ruff, pytest-mock, etc.)
- **Inputs**: Active venv, pyproject.toml
- **Outputs**: All runtime + dev packages installed
- **Edge cases**: Same as FR-2

### FR-4: Local development server
- **What**: `make local-dev` starts uvicorn with hot reload on port 8000
- **Inputs**: Active venv with deps installed, app.py
- **Outputs**: Running FastAPI server at http://localhost:8000
- **Edge cases**: Port already in use, app.py not yet created (will fail gracefully)

### FR-5: Local test runner
- **What**: `make local-test` runs pytest with verbose output and short tracebacks
- **Inputs**: Active venv with dev deps, tests/ directory
- **Outputs**: Test results on stdout
- **Edge cases**: No tests exist yet (pytest exits with no-tests-collected)

### FR-6: Local linter
- **What**: `make local-lint` runs ruff check and ruff format check
- **Inputs**: Active venv with dev deps, source files
- **Outputs**: Lint/format results on stdout
- **Edge cases**: No Python files to lint

### FR-7: Docker dev target
- **What**: `make dev` runs `docker-compose up --build` for local Docker development
- **Inputs**: docker-compose.yml, Dockerfile
- **Outputs**: Running containerized app
- **Edge cases**: Docker not installed, docker-compose.yml not yet created (will fail with clear error)

### FR-8: Docker test target
- **What**: `make test` runs pytest inside a Docker container
- **Inputs**: docker-compose.yml, Dockerfile
- **Outputs**: Test results from container
- **Edge cases**: Same as FR-7

---

## Tangible Outcomes

- [ ] **Outcome 1**: `make venv` creates a `venv/` directory with Python 3.12
- [ ] **Outcome 2**: `make install-dev` installs all runtime + dev dependencies successfully
- [ ] **Outcome 3**: `make local-test` runs pytest and exits (even if no tests exist yet)
- [ ] **Outcome 4**: `make local-lint` runs ruff check + format and exits cleanly
- [ ] **Outcome 5**: All 8 Makefile targets exist and are documented with `.PHONY`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_makefile_exists**: Verify Makefile exists at project root
2. **test_makefile_has_all_targets**: Parse Makefile and verify all 8 targets are defined (venv, install, install-dev, local-dev, local-test, local-lint, dev, test)
3. **test_makefile_phony_targets**: Verify `.PHONY` declaration includes all targets
4. **test_venv_target_creates_virtualenv**: Run `make venv` and verify venv/ directory is created
5. **test_install_dev_succeeds**: Run `make install-dev` and verify key packages are importable
6. **test_local_test_runs_pytest**: Run `make local-test` and verify pytest executes
7. **test_local_lint_runs_ruff**: Run `make local-lint` and verify ruff executes

### Mocking Strategy
- No external services to mock -- these are shell commands
- Tests run actual make targets (integration-style tests)
- Docker targets (dev, test) are tested for presence only, not execution (Docker may not be available in CI)

### Coverage Expectation
- All 8 targets verified for existence
- Core targets (venv, install-dev, local-test, local-lint) verified for correct execution

---

## References
- roadmap.md, design.md
- pyproject.toml (S1.1 -- already done)
