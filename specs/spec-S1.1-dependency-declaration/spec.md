# Spec S1.1 -- Dependency Declaration

## Overview
Declare all runtime and development dependencies in a single `pyproject.toml` file (PEP 621) and provide a `.env.example` template listing every required environment variable. This is the foundational spec -- no other spec can install packages without this being in place first.

## Dependencies
None (this is the root spec).

## Target Location
`pyproject.toml`, `.env.example`

---

## Functional Requirements

### FR-1: pyproject.toml with PEP 621 metadata
- **What**: Create a `pyproject.toml` at project root with full project metadata and dependency lists
- **Inputs**: N/A (static file)
- **Outputs**: Valid `pyproject.toml` parseable by pip/uv
- **Details**:
  - `[project]` section: name="equityiq", version="0.1.0", requires-python=">=3.12"
  - Runtime dependencies: google-adk, google-generativeai, fastapi, uvicorn, pydantic, pydantic-settings, httpx, aiohttp, cachetools, aiosqlite, xgboost, scikit-learn, pandas, numpy, python-dotenv, beautifulsoup4, lxml, colorlog
  - `[project.optional-dependencies]` dev group: pytest, pytest-asyncio, ruff, pytest-mock, httpx (test client)

### FR-2: Ruff configuration in pyproject.toml
- **What**: Include `[tool.ruff]` section with project linting standards
- **Inputs**: N/A
- **Outputs**: `ruff check` and `ruff format` use these settings
- **Details**:
  - `line-length = 100`
  - `target-version = "py312"`
  - Select rules: at minimum "E", "F", "I" (pyflakes, pycodestyle, isort)

### FR-3: Pytest configuration in pyproject.toml
- **What**: Include `[tool.pytest.ini_options]` section
- **Inputs**: N/A
- **Outputs**: `pytest` picks up config automatically
- **Details**:
  - `asyncio_mode = "auto"` for pytest-asyncio
  - `testpaths = ["tests"]`

### FR-4: .env.example template
- **What**: Create `.env.example` listing all required environment variables with placeholder values
- **Inputs**: N/A
- **Outputs**: Developers copy to `.env` and fill in real values
- **Details**:
  - Variables: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY, ENVIRONMENT (default: local), SQLITE_DB_PATH (default: data/equityiq.db), GCP_PROJECT_ID, GCP_REGION, LOG_LEVEL (default: INFO)
  - Each variable has a comment explaining its purpose
  - No real secrets -- only placeholder values like `your-api-key-here`

### FR-5: .env in .gitignore
- **What**: Ensure `.env` (but not `.env.example`) is listed in `.gitignore`
- **Inputs**: N/A
- **Outputs**: Real secrets never committed to git
- **Edge cases**: `.gitignore` may already exist -- append if needed, don't duplicate

---

## Tangible Outcomes

- [ ] **Outcome 1**: `pyproject.toml` exists at project root and is valid TOML
- [ ] **Outcome 2**: `pip install -e .` (or `uv pip install -e .`) succeeds without errors
- [ ] **Outcome 3**: `pip install -e ".[dev]"` installs pytest, ruff, and pytest-mock
- [ ] **Outcome 4**: `ruff check --config pyproject.toml` runs with line-length=100
- [ ] **Outcome 5**: `.env.example` lists all 9 environment variables with comments
- [ ] **Outcome 6**: `.env` is in `.gitignore`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_pyproject_exists**: Assert `pyproject.toml` exists at project root
2. **test_pyproject_valid_toml**: Parse `pyproject.toml` with `tomllib` -- no errors
3. **test_pyproject_has_runtime_deps**: Assert all 17 runtime dependencies are listed
4. **test_pyproject_has_dev_deps**: Assert dev dependencies include pytest, pytest-asyncio, ruff, pytest-mock
5. **test_pyproject_python_version**: Assert requires-python >= 3.12
6. **test_ruff_config**: Assert `[tool.ruff]` has line-length=100 and target-version="py312"
7. **test_pytest_config**: Assert asyncio_mode="auto" and testpaths=["tests"]
8. **test_env_example_exists**: Assert `.env.example` exists
9. **test_env_example_has_all_vars**: Assert all 9 required variables are present
10. **test_gitignore_excludes_env**: Assert `.env` appears in `.gitignore`

### Mocking Strategy
- No mocking needed -- these are static file validation tests

### Coverage Expectation
- 100% of functional requirements covered by file-content assertions

---

## References
- roadmap.md (Phase 1, S1.1)
- design.md (Tech Stack section)
- PEP 621 (pyproject.toml metadata standard)
