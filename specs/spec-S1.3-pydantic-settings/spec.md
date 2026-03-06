# Spec S1.3 -- Pydantic Settings Configuration

## Overview
Centralized, type-safe configuration using pydantic-settings. All environment variables are loaded from `.env` via a single `Settings` class. No module in the project should read `os.environ` directly -- always go through `config/settings.py`.

## Dependencies
- S1.1 (pyproject.toml must declare `pydantic-settings` and `python-dotenv`)

## Target Location
`config/settings.py`

---

## Functional Requirements

### FR-1: Settings class with pydantic-settings BaseSettings
- **What**: A `Settings` class inheriting from `pydantic_settings.BaseSettings` that loads all config from environment variables / `.env` file
- **Inputs**: Environment variables or `.env` file
- **Outputs**: Typed, validated `Settings` instance
- **Details**:
  - Uses `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`
  - All fields have type annotations and sensible defaults where appropriate

### FR-2: API key fields (no defaults -- required in production)
- **What**: Four API key fields that are optional (defaulting to empty string) for local dev flexibility
- **Fields**:
  - `GOOGLE_API_KEY: str = ""`
  - `POLYGON_API_KEY: str = ""`
  - `FRED_API_KEY: str = ""`
  - `NEWS_API_KEY: str = ""`
- **Edge cases**: Empty string allows startup without keys (agents fail gracefully on use). Tests never need real keys.

### FR-3: Environment and infrastructure fields
- **What**: Fields controlling runtime behavior
- **Fields**:
  - `ENVIRONMENT: str = "local"` -- "local" or "production"
  - `SQLITE_DB_PATH: str = "data/equityiq.db"`
  - `GCP_PROJECT_ID: str = ""`
  - `GCP_REGION: str = "us-central1"`
  - `LOG_LEVEL: str = "INFO"`

### FR-4: Agent URL fields
- **What**: Base URLs for each agent (used in local mode, overridden in production)
- **Fields**:
  - `VALUATION_AGENT_URL: str = "http://localhost:8001"`
  - `MOMENTUM_AGENT_URL: str = "http://localhost:8002"`
  - `PULSE_AGENT_URL: str = "http://localhost:8003"`
  - `ECONOMY_AGENT_URL: str = "http://localhost:8004"`
  - `COMPLIANCE_AGENT_URL: str = "http://localhost:8005"`
  - `SYNTHESIZER_AGENT_URL: str = "http://localhost:8006"`
  - `RISK_AGENT_URL: str = "http://localhost:8007"`

### FR-5: Computed property -- is_production
- **What**: `@property` that returns `True` when `ENVIRONMENT == "production"`
- **Rationale**: Avoids string comparison scattered throughout codebase

### FR-6: Singleton accessor -- get_settings()
- **What**: Module-level `get_settings()` function using `@lru_cache` to return a single `Settings` instance
- **Rationale**: Avoids re-parsing `.env` on every import. Single source of truth.
- **Details**: Uses `functools.lru_cache(maxsize=1)`

### FR-7: config/__init__.py re-export
- **What**: `config/__init__.py` must export `Settings` and `get_settings` for clean imports
- **Usage**: `from config import get_settings` or `from config.settings import Settings`

---

## Tangible Outcomes

- [ ] **Outcome 1**: `config/settings.py` exists with `Settings(BaseSettings)` class
- [ ] **Outcome 2**: `config/__init__.py` exports `Settings` and `get_settings`
- [ ] **Outcome 3**: All 9 core env vars from `.env.example` have corresponding fields
- [ ] **Outcome 4**: All 7 agent URL fields present with correct default ports
- [ ] **Outcome 5**: `get_settings()` returns cached singleton (same object on repeated calls)
- [ ] **Outcome 6**: `is_production` property works correctly
- [ ] **Outcome 7**: Settings loads from `.env` file when present
- [ ] **Outcome 8**: All tests pass: `python -m pytest tests/test_settings.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)

1. **test_settings_class_exists**: Import `Settings` from `config.settings` -- no ImportError
2. **test_settings_is_base_settings**: Assert `Settings` is a subclass of `pydantic_settings.BaseSettings`
3. **test_settings_has_api_key_fields**: Assert fields: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY
4. **test_settings_has_infra_fields**: Assert fields: ENVIRONMENT, SQLITE_DB_PATH, GCP_PROJECT_ID, GCP_REGION, LOG_LEVEL
5. **test_settings_has_agent_url_fields**: Assert all 7 agent URL fields with correct defaults
6. **test_settings_default_values**: Instantiate `Settings()` with no env -- check defaults (ENVIRONMENT="local", LOG_LEVEL="INFO", etc.)
7. **test_settings_api_keys_default_empty**: Instantiate `Settings()` -- all API keys default to ""
8. **test_is_production_property_local**: `Settings(ENVIRONMENT="local").is_production` is `False`
9. **test_is_production_property_production**: `Settings(ENVIRONMENT="production").is_production` is `True`
10. **test_get_settings_returns_settings**: `get_settings()` returns a `Settings` instance
11. **test_get_settings_is_cached**: `get_settings() is get_settings()` (same object)
12. **test_settings_from_env_vars**: Set env vars via monkeypatch, instantiate Settings, verify values loaded
13. **test_config_init_exports**: `from config import Settings, get_settings` works without error

### Mocking Strategy
- Use `monkeypatch.setenv()` to set environment variables in tests
- Use `monkeypatch.delenv()` to clear env vars
- Clear `lru_cache` between tests with `get_settings.cache_clear()`

### Coverage Expectation
- 100% of Settings fields tested
- All properties and the singleton accessor tested

---

## References
- roadmap.md (Phase 1, S1.3)
- `.env.example` (variable names and defaults)
- pydantic-settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
