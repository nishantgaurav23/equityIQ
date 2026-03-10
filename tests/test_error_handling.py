"""Tests for S9.4 -- API Error Taxonomy."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.exceptions import (
    AnalysisTimeoutError,
    EquityIQError,
    InsufficientDataError,
    InvalidTickerError,
    TickerNotFoundError,
    VerdictNotFoundError,
)
from api.routes import router


def _create_test_app():
    """Create a test app with error handlers registered."""
    from api.error_handlers import register_error_handlers

    test_app = FastAPI()
    register_error_handlers(test_app)
    test_app.include_router(router)

    # Mock all app.state dependencies
    test_app.state.conductor = MagicMock()
    test_app.state.vault = MagicMock()
    test_app.state.history_retriever = MagicMock()
    test_app.state.settings = MagicMock()
    test_app.state.settings.ENVIRONMENT = "test"

    return test_app


@pytest.fixture
def app():
    return _create_test_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class TestExceptionHierarchy:
    """FR-1: All exceptions inherit from EquityIQError with correct attributes."""

    def test_base_exception(self):
        err = EquityIQError("something broke", error_code="GENERIC")
        assert isinstance(err, Exception)
        assert err.message == "something broke"
        assert err.error_code == "GENERIC"
        assert err.details == {}

    def test_base_exception_with_details(self):
        err = EquityIQError("oops", error_code="X", details={"key": "val"})
        assert err.details == {"key": "val"}

    def test_ticker_not_found_inherits(self):
        err = TickerNotFoundError("XYZ")
        assert isinstance(err, EquityIQError)
        assert err.error_code == "TICKER_NOT_FOUND"
        assert "XYZ" in err.message

    def test_analysis_timeout_inherits(self):
        err = AnalysisTimeoutError("AAPL")
        assert isinstance(err, EquityIQError)
        assert err.error_code == "ANALYSIS_TIMEOUT"
        assert "AAPL" in err.message

    def test_insufficient_data_inherits(self):
        err = InsufficientDataError("AAPL")
        assert isinstance(err, EquityIQError)
        assert err.error_code == "INSUFFICIENT_DATA"
        assert "AAPL" in err.message

    def test_invalid_ticker_inherits(self):
        err = InvalidTickerError("!!!")
        assert isinstance(err, EquityIQError)
        assert err.error_code == "INVALID_TICKER"
        assert "!!!" in err.message

    def test_verdict_not_found_inherits(self):
        err = VerdictNotFoundError("sess-123")
        assert isinstance(err, EquityIQError)
        assert err.error_code == "VERDICT_NOT_FOUND"
        assert "sess-123" in err.message


class TestStructuredErrorResponse:
    """FR-2 & FR-3: Error responses follow structured JSON schema."""

    def test_invalid_ticker_returns_400(self, client, app):
        """Invalid ticker format -> 400 with INVALID_TICKER code."""
        resp = client.post("/api/v1/analyze/VERYLONGTICKERSYMBOLNAME")
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_TICKER"
        assert "message" in data["error"]
        assert "details" in data["error"]

    def test_ticker_not_found_returns_404(self, client, app):
        """TickerNotFoundError raised by conductor -> 404."""
        app.state.conductor.analyze = AsyncMock(side_effect=TickerNotFoundError("FAKECO"))
        resp = client.post("/api/v1/analyze/FAKECO")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "TICKER_NOT_FOUND"

    def test_analysis_timeout_returns_504(self, client, app):
        """asyncio.TimeoutError from conductor -> 504."""
        app.state.conductor.analyze = AsyncMock(side_effect=asyncio.TimeoutError())
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 504
        data = resp.json()
        assert data["error"]["code"] == "ANALYSIS_TIMEOUT"

    def test_analysis_timeout_domain_error_returns_504(self, client, app):
        """AnalysisTimeoutError raised explicitly -> 504."""
        app.state.conductor.analyze = AsyncMock(side_effect=AnalysisTimeoutError("AAPL"))
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 504
        data = resp.json()
        assert data["error"]["code"] == "ANALYSIS_TIMEOUT"

    def test_insufficient_data_returns_422(self, client, app):
        """InsufficientDataError -> 422."""
        app.state.conductor.analyze = AsyncMock(side_effect=InsufficientDataError("AAPL"))
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 422
        data = resp.json()
        assert data["error"]["code"] == "INSUFFICIENT_DATA"

    def test_verdict_not_found_returns_404(self, client, app):
        """Missing session_id -> 404 with VERDICT_NOT_FOUND."""
        app.state.vault.get_verdict = AsyncMock(return_value=None)
        resp = client.get("/api/v1/verdict/nonexistent")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "VERDICT_NOT_FOUND"

    def test_unhandled_exception_returns_500(self, client, app):
        """Random exception -> 500 with INTERNAL_ERROR."""
        app.state.conductor.analyze = AsyncMock(side_effect=RuntimeError("unexpected crash"))
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_error_response_has_no_traceback(self, client, app):
        """500 response body does not contain traceback info."""
        app.state.conductor.analyze = AsyncMock(
            side_effect=RuntimeError("crash at /some/file.py:42")
        )
        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 500
        body = resp.text
        assert "Traceback" not in body
        assert "/some/file.py" not in body
        assert data_has_no_traceback(resp.json())

    def test_portfolio_invalid_ticker_structured_error(self, client, app):
        """Portfolio endpoint with bad ticker returns structured error."""
        resp = client.post("/api/v1/portfolio", json={"tickers": ["VERYLONGTICKERSYMBOLNAME"]})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_TICKER"

    def test_portfolio_timeout_structured_error(self, client, app):
        """Portfolio endpoint timeout returns structured error."""
        app.state.conductor.analyze_portfolio = AsyncMock(side_effect=asyncio.TimeoutError())
        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL"]})
        assert resp.status_code == 504
        data = resp.json()
        assert data["error"]["code"] == "ANALYSIS_TIMEOUT"

    def test_history_empty_ticker_structured_error(self, client, app):
        """History endpoint with empty ticker returns structured error."""
        resp = client.get("/api/v1/history/%20/trend")
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "INVALID_TICKER"


def data_has_no_traceback(data: dict) -> bool:
    """Verify error response doesn't leak internal details."""
    error_msg = data.get("error", {}).get("message", "")
    assert "Traceback" not in error_msg
    assert ".py" not in error_msg
    return True
