# Checklist S1.3 -- Pydantic Settings Configuration

## Test File
- [x] `tests/test_settings.py` created with all 14 test cases

## Implementation
- [x] `config/__init__.py` created with re-exports
- [x] `config/settings.py` created with `Settings(BaseSettings)` class
- [x] API key fields: GOOGLE_API_KEY, POLYGON_API_KEY, FRED_API_KEY, NEWS_API_KEY
- [x] Infra fields: ENVIRONMENT, SQLITE_DB_PATH, GCP_PROJECT_ID, GCP_REGION, LOG_LEVEL
- [x] Agent URL fields: 7 URLs with correct default ports
- [x] `is_production` computed property
- [x] `get_settings()` singleton with `@lru_cache`
- [x] `SettingsConfigDict` with `env_file=".env"`, `extra="ignore"`

## Verification
- [x] All 14 tests pass: `python -m pytest tests/test_settings.py -v`
- [x] `ruff check config/settings.py` passes
- [x] `ruff check tests/test_settings.py` passes
- [x] Settings loads from env vars (tested via monkeypatch)
- [x] Singleton caching works (same object returned)

## Bonus Fix
- [x] Fixed `pyproject.toml` setuptools package discovery (added `[tool.setuptools.packages.find]`)
