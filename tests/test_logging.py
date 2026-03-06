"""Tests for config/logging.py -- structured logging setup (S1.5)."""

import io
import json
import logging

import pytest

from config.settings import Settings


class TestImports:
    """Verify all public symbols are importable."""

    def test_setup_logging_importable(self):
        from config.logging import setup_logging  # noqa: F401

    def test_get_logger_importable(self):
        from config.logging import get_logger  # noqa: F401

    def test_request_id_var_importable(self):
        from config.logging import request_id_var  # noqa: F401

    def test_config_init_exports_logging(self):
        from config import get_logger, setup_logging  # noqa: F401


class TestGetLogger:
    """Tests for get_logger() convenience function."""

    def test_get_logger_returns_logger(self):
        from config.logging import get_logger

        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_name(self):
        from config.logging import get_logger

        logger = get_logger("mymodule")
        assert logger.name == "mymodule"


class TestSetupLogging:
    """Tests for setup_logging() configuration."""

    def _make_settings(self, **overrides):
        defaults = {"ENVIRONMENT": "local", "LOG_LEVEL": "INFO"}
        defaults.update(overrides)
        return Settings(**defaults)

    def test_setup_logging_sets_level(self):
        from config.logging import setup_logging

        settings = self._make_settings(LOG_LEVEL="DEBUG")
        setup_logging(settings)
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_sets_level_warning(self):
        from config.logging import setup_logging

        settings = self._make_settings(LOG_LEVEL="WARNING")
        setup_logging(settings)
        assert logging.getLogger().level == logging.WARNING

    def test_setup_logging_local_uses_stream_handler(self):
        from config.logging import setup_logging

        settings = self._make_settings(ENVIRONMENT="local")
        setup_logging(settings)
        root = logging.getLogger()
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    def test_setup_logging_clears_existing_handlers(self):
        from config.logging import setup_logging

        settings = self._make_settings()
        setup_logging(settings)
        setup_logging(settings)
        root = logging.getLogger()
        # Should have exactly 1 handler, not 2
        assert len(root.handlers) == 1


class TestRequestId:
    """Tests for request_id context variable."""

    def test_request_id_var_default(self):
        from config.logging import request_id_var

        # Reset to default by creating a new context or checking default
        token = request_id_var.set("no-request-id")
        try:
            assert request_id_var.get() == "no-request-id"
        finally:
            request_id_var.reset(token)

    def test_set_and_get_request_id(self):
        from config.logging import get_request_id, request_id_var, set_request_id

        token = request_id_var.set("no-request-id")
        try:
            set_request_id("abc-123")
            assert get_request_id() == "abc-123"
        finally:
            request_id_var.reset(token)


class TestFormatters:
    """Tests for local vs production log output format."""

    def _capture_log_output(self, environment: str, message: str) -> str:
        """Configure logging for given env, emit a message, return output."""
        from config.logging import setup_logging

        settings = Settings(ENVIRONMENT=environment, LOG_LEVEL="INFO")
        setup_logging(settings)

        root = logging.getLogger()
        # Replace handler's stream with a StringIO to capture output
        stream = io.StringIO()
        for handler in root.handlers:
            handler.stream = stream

        test_logger = logging.getLogger("test_formatter")
        test_logger.info(message)

        return stream.getvalue()

    def test_production_formatter_json_output(self):
        output = self._capture_log_output("production", "test message")
        parsed = json.loads(output.strip())
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test_formatter"
        assert parsed["message"] == "test message"
        assert "timestamp" in parsed
        assert "request_id" in parsed

    def test_local_formatter_not_json(self):
        output = self._capture_log_output("local", "hello world")
        with pytest.raises(json.JSONDecodeError):
            json.loads(output.strip())
        assert "hello world" in output
