# Spec S1.5 -- Structured Logging Setup

## Overview
Centralized logging configuration for EquityIQ. Colorlog-formatted output for local development, structured JSON for production. LOG_LEVEL sourced from `config/settings.py`. Includes `request_id` context variable for request tracing across agents.

## Dependencies
- S1.3 (config/settings.py must provide `LOG_LEVEL` and `ENVIRONMENT` / `is_production`)

## Target Location
`config/logging.py`

---

## Functional Requirements

### FR-1: setup_logging() function
- **What**: A `setup_logging(settings: Settings | None = None)` function that configures the root logger
- **Inputs**: Optional `Settings` instance (defaults to `get_settings()` if not provided)
- **Outputs**: None (configures logging module in-place)
- **Details**:
  - Clears existing handlers on root logger before configuring
  - Sets root logger level from `settings.LOG_LEVEL`
  - Selects formatter based on `settings.is_production`

### FR-2: Local development formatter (colorlog)
- **What**: When `ENVIRONMENT != "production"`, use `colorlog.ColoredFormatter`
- **Format**: `%(log_color)s%(levelname)-8s%(reset)s %(cyan)s%(name)s%(reset)s | %(message)s`
- **Colors**: DEBUG=white, INFO=green, WARNING=yellow, ERROR=red, CRITICAL=bold_red

### FR-3: Production formatter (JSON)
- **What**: When `ENVIRONMENT == "production"`, use `logging.Formatter` producing JSON-like structured output
- **Format**: JSON with keys: `timestamp`, `level`, `logger`, `message`, `request_id`
- **Details**: Uses `logging.Formatter` with a custom `format()` method or a simple JSON formatter class
- **Rationale**: Cloud Logging (GCP) parses structured JSON automatically

### FR-4: request_id context variable
- **What**: A `contextvars.ContextVar` named `request_id_var` for tracing requests across log lines
- **Default**: `"no-request-id"`
- **Usage**: Production JSON formatter includes `request_id` field. A `get_request_id()` helper returns the current value.
- **Details**: Also provide `set_request_id(rid: str)` to set it (used by middleware later)

### FR-5: get_logger() convenience function
- **What**: `get_logger(name: str) -> logging.Logger` that returns `logging.getLogger(name)`
- **Rationale**: Consistent import pattern: `from config.logging import get_logger`

### FR-6: config/__init__.py re-export
- **What**: `config/__init__.py` must also export `setup_logging` and `get_logger`
- **Usage**: `from config import setup_logging, get_logger`

### FR-7: Integration with app.py
- **What**: `app.py` should call `setup_logging()` during lifespan startup (before first log line)
- **Details**: Call `setup_logging(settings)` at the top of the lifespan context manager, before `logger.info("EquityIQ starting up...")`

---

## Tangible Outcomes

- [ ] **Outcome 1**: `config/logging.py` exists with `setup_logging()`, `get_logger()`, `request_id_var`, `get_request_id()`, `set_request_id()`
- [ ] **Outcome 2**: `config/__init__.py` exports `setup_logging` and `get_logger`
- [ ] **Outcome 3**: Local mode uses colorlog with colored level names
- [ ] **Outcome 4**: Production mode outputs structured JSON with timestamp, level, logger, message, request_id
- [ ] **Outcome 5**: `request_id_var` is a `contextvars.ContextVar` with default `"no-request-id"`
- [ ] **Outcome 6**: `app.py` calls `setup_logging(settings)` in lifespan before any logging
- [ ] **Outcome 7**: LOG_LEVEL from settings controls root logger level
- [ ] **Outcome 8**: All tests pass: `python -m pytest tests/test_logging.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)

1. **test_setup_logging_importable**: Import `setup_logging` from `config.logging` -- no ImportError
2. **test_get_logger_importable**: Import `get_logger` from `config.logging` -- no ImportError
3. **test_get_logger_returns_logger**: `get_logger("test")` returns a `logging.Logger` instance
4. **test_get_logger_name**: `get_logger("mymodule").name == "mymodule"`
5. **test_setup_logging_sets_level**: Call `setup_logging()` with LOG_LEVEL="DEBUG", verify root logger level is DEBUG
6. **test_setup_logging_sets_level_warning**: Call with LOG_LEVEL="WARNING", verify root logger level is WARNING
7. **test_setup_logging_local_uses_stream_handler**: In local mode, root logger has a StreamHandler
8. **test_setup_logging_clears_existing_handlers**: Call setup_logging twice, verify no duplicate handlers
9. **test_request_id_var_default**: `request_id_var.get()` returns `"no-request-id"` when not set
10. **test_set_and_get_request_id**: Call `set_request_id("abc-123")`, then `get_request_id()` returns `"abc-123"`
11. **test_production_formatter_json_output**: In production mode, capture log output and verify it contains JSON with expected keys
12. **test_local_formatter_not_json**: In local mode, capture log output and verify it is NOT JSON
13. **test_config_init_exports_logging**: `from config import setup_logging, get_logger` works without error

### Mocking Strategy
- Use `monkeypatch.setenv()` for ENVIRONMENT and LOG_LEVEL
- Create fresh `Settings` instances for each test
- Use `caplog` or `io.StringIO` with a handler to capture log output
- Reset root logger handlers in test teardown

### Coverage Expectation
- 100% of public functions tested
- Both local and production code paths covered

---

## References
- roadmap.md (Phase 1, S1.5)
- config/settings.py (LOG_LEVEL, ENVIRONMENT, is_production)
- colorlog docs: https://github.com/borntyping/python-colorlog
- Python logging cookbook: https://docs.python.org/3/howto/logging-cookbook.html
