"""Tests for api/routes.py -- API endpoint tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router
from config.data_contracts import FinalVerdict, PortfolioInsight
from memory.history_retriever import SignalSnapshot


def _sample_verdict(ticker="AAPL", signal="BUY", confidence=0.75):
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        session_id="test-session-123",
    )


def _sample_snapshot(
    ticker="AAPL", signal="BUY", confidence=0.72, created_at="2026-03-05T10:00:00Z"
):
    return SignalSnapshot(
        session_id="snap-123",
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        created_at=created_at,
    )


@pytest.fixture
def app():
    """Create a minimal test app with the API router and mocked state."""
    from api.error_handlers import register_error_handlers

    test_app = FastAPI()
    register_error_handlers(test_app)
    test_app.include_router(router)

    # Mock all app.state dependencies
    test_app.state.conductor = MagicMock()
    test_app.state.vault = MagicMock()
    test_app.state.history_retriever = MagicMock()

    return test_app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class TestAnalyzeEndpoint:
    def test_analyze_success(self, client, app):
        """POST /api/v1/analyze/AAPL returns FinalVerdict."""
        verdict = _sample_verdict()
        app.state.conductor.analyze = AsyncMock(return_value=verdict)

        resp = client.post("/api/v1/analyze/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"
        assert data["final_signal"] == "BUY"

    def test_analyze_invalid_ticker(self, client, app):
        """Too-long ticker returns 400."""
        resp = client.post("/api/v1/analyze/VERYLONGTICKERSYMBOLNAME")
        assert resp.status_code == 400

    def test_analyze_normalizes_ticker(self, client, app):
        """Ticker is passed uppercase."""
        verdict = _sample_verdict()
        app.state.conductor.analyze = AsyncMock(return_value=verdict)

        client.post("/api/v1/analyze/aapl")
        app.state.conductor.analyze.assert_awaited_once()
        call_arg = app.state.conductor.analyze.call_args[0][0]
        assert call_arg == "AAPL"


class TestHistoryEndpoints:
    def test_ticker_history(self, client, app):
        """GET /api/v1/history/AAPL returns list of verdicts."""
        verdicts = [_sample_verdict(), _sample_verdict(signal="SELL")]
        app.state.history_retriever.get_ticker_history = AsyncMock(return_value=verdicts)

        resp = client.get("/api/v1/history/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_recent_history(self, client, app):
        """GET /api/v1/history returns recent verdicts."""
        verdicts = [_sample_verdict()]
        app.state.history_retriever.get_recent_verdicts = AsyncMock(return_value=verdicts)

        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_history_pagination(self, client, app):
        """Limit and offset params are passed through."""
        app.state.history_retriever.get_ticker_history = AsyncMock(return_value=[])

        resp = client.get("/api/v1/history/AAPL?limit=5&offset=10")
        assert resp.status_code == 200
        app.state.history_retriever.get_ticker_history.assert_awaited_once_with(
            "AAPL", limit=5, offset=10
        )


class TestHistoryEndpointsS93:
    """S9.3-specific tests for history and trend endpoints."""

    def test_trend_endpoint_success(self, client, app):
        """GET /api/v1/history/AAPL/trend returns list of SignalSnapshot."""
        snapshots = [
            _sample_snapshot(created_at="2026-03-01T10:00:00Z", signal="HOLD", confidence=0.65),
            _sample_snapshot(created_at="2026-03-05T10:00:00Z", signal="BUY", confidence=0.72),
        ]
        app.state.history_retriever.get_signal_trend = AsyncMock(return_value=snapshots)

        resp = client.get("/api/v1/history/AAPL/trend")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["final_signal"] == "HOLD"
        assert data[1]["final_signal"] == "BUY"
        assert data[0]["overall_confidence"] == 0.65
        assert data[1]["ticker"] == "AAPL"

    def test_trend_endpoint_empty_ticker(self, client, app):
        """Empty ticker (whitespace only) returns 400."""
        resp = client.get("/api/v1/history/%20/trend")
        assert resp.status_code == 400

    def test_trend_endpoint_normalizes_ticker(self, client, app):
        """Ticker is normalized to uppercase before calling retriever."""
        app.state.history_retriever.get_signal_trend = AsyncMock(return_value=[])

        client.get("/api/v1/history/aapl/trend")
        app.state.history_retriever.get_signal_trend.assert_awaited_once()
        call_args = app.state.history_retriever.get_signal_trend.call_args
        assert call_args[0][0] == "AAPL"

    def test_trend_endpoint_limit_param(self, client, app):
        """Limit query param is passed to get_signal_trend."""
        app.state.history_retriever.get_signal_trend = AsyncMock(return_value=[])

        client.get("/api/v1/history/AAPL/trend?limit=50")
        app.state.history_retriever.get_signal_trend.assert_awaited_once_with("AAPL", limit=50)

    def test_trend_endpoint_default_limit(self, client, app):
        """Default limit=20 when not specified."""
        app.state.history_retriever.get_signal_trend = AsyncMock(return_value=[])

        client.get("/api/v1/history/AAPL/trend")
        app.state.history_retriever.get_signal_trend.assert_awaited_once_with("AAPL", limit=20)

    def test_trend_endpoint_empty_result(self, client, app):
        """Unknown ticker returns 200 with empty list."""
        app.state.history_retriever.get_signal_trend = AsyncMock(return_value=[])

        resp = client.get("/api/v1/history/UNKNOWN/trend")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_ticker_history_invalid_ticker(self, client, app):
        """Whitespace-only ticker returns 400."""
        resp = client.get("/api/v1/history/%20")
        assert resp.status_code == 400

    def test_recent_history_default_params(self, client, app):
        """GET /api/v1/history with defaults calls retriever correctly."""
        app.state.history_retriever.get_recent_verdicts = AsyncMock(return_value=[])

        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        app.state.history_retriever.get_recent_verdicts.assert_awaited_once_with(limit=20, offset=0)


class TestVerdictEndpoint:
    def test_get_verdict_found(self, client, app):
        """GET /api/v1/verdict/{session_id} returns verdict."""
        verdict = _sample_verdict()
        app.state.vault.get_verdict = AsyncMock(return_value=verdict)

        resp = client.get("/api/v1/verdict/test-session-123")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "test-session-123"

    def test_get_verdict_not_found(self, client, app):
        """Unknown session_id returns 404."""
        app.state.vault.get_verdict = AsyncMock(return_value=None)

        resp = client.get("/api/v1/verdict/nonexistent")
        assert resp.status_code == 404


def _sample_portfolio_insight(tickers=None):
    tickers = tickers or ["AAPL", "TSLA"]
    verdicts = [_sample_verdict(t) for t in tickers]
    return PortfolioInsight(
        tickers=tickers,
        verdicts=verdicts,
        portfolio_signal="BUY",
        diversification_score=0.65,
        top_pick="AAPL",
    )


class TestPortfolioEndpoint:
    def test_portfolio_success(self, client, app):
        """POST /api/v1/portfolio returns PortfolioInsight."""
        insight = _sample_portfolio_insight()
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=insight)

        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL", "TSLA"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["portfolio_signal"] == "BUY"
        assert data["tickers"] == ["AAPL", "TSLA"]
        assert len(data["verdicts"]) == 2
        assert data["top_pick"] == "AAPL"

    def test_portfolio_empty_tickers(self, client, app):
        """Empty tickers list returns 422."""
        resp = client.post("/api/v1/portfolio", json={"tickers": []})
        assert resp.status_code == 422

    def test_portfolio_too_many_tickers(self, client, app):
        """More than 10 tickers returns 422."""
        tickers = [f"T{i}" for i in range(11)]
        resp = client.post("/api/v1/portfolio", json={"tickers": tickers})
        assert resp.status_code == 422

    def test_portfolio_invalid_ticker_format(self, client, app):
        """Ticker too long returns 400."""
        resp = client.post("/api/v1/portfolio", json={"tickers": ["VERYLONGTICKERSYMBOLNAME"]})
        assert resp.status_code == 400

    def test_portfolio_normalizes_tickers(self, client, app):
        """Lowercase tickers are passed as uppercase to conductor."""
        insight = _sample_portfolio_insight()
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=insight)

        client.post("/api/v1/portfolio", json={"tickers": ["aapl", "tsla"]})
        app.state.conductor.analyze_portfolio.assert_awaited_once()
        call_arg = app.state.conductor.analyze_portfolio.call_args[0][0]
        assert call_arg == ["AAPL", "TSLA"]

    def test_portfolio_single_ticker(self, client, app):
        """Single ticker works fine."""
        insight = _sample_portfolio_insight(["AAPL"])
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=insight)

        resp = client.post("/api/v1/portfolio", json={"tickers": ["AAPL"]})
        assert resp.status_code == 200
        assert resp.json()["tickers"] == ["AAPL"]


class TestAgentsEndpoint:
    def test_list_agents(self, client, app):
        """GET /api/v1/agents returns agent list."""
        mock_agent = MagicMock()
        mock_agent.name = "valuation_scout"
        mock_agent.get_agent_card.return_value = {"name": "valuation_scout"}
        app.state.conductor._lazy_load_agents = MagicMock(return_value=[mock_agent])

        resp = client.get("/api/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "valuation_scout"
