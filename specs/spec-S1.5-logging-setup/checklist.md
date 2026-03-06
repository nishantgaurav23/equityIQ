# Checklist S1.5 -- Structured Logging Setup

## Implementation Progress

### Tests (write first -- TDD)
- [x] test_setup_logging_importable
- [x] test_get_logger_importable
- [x] test_get_logger_returns_logger
- [x] test_get_logger_name
- [x] test_setup_logging_sets_level
- [x] test_setup_logging_sets_level_warning
- [x] test_setup_logging_local_uses_stream_handler
- [x] test_setup_logging_clears_existing_handlers
- [x] test_request_id_var_default
- [x] test_set_and_get_request_id
- [x] test_production_formatter_json_output
- [x] test_local_formatter_not_json
- [x] test_config_init_exports_logging

### Implementation
- [x] Create `config/logging.py` with `setup_logging()`, `get_logger()`, request_id helpers
- [x] Local formatter using colorlog
- [x] Production formatter outputting structured JSON
- [x] `request_id_var` ContextVar with default
- [x] `set_request_id()` and `get_request_id()` helpers
- [x] Update `config/__init__.py` to export `setup_logging` and `get_logger`
- [x] Wire `setup_logging()` into `app.py` lifespan

### Verification
- [x] All tests pass: `python -m pytest tests/test_logging.py -v`
- [x] Ruff lint passes: `ruff check config/logging.py tests/test_logging.py`
- [x] No existing tests broken: `python -m pytest tests/ -v`
- [x] Roadmap status updated to `done`
