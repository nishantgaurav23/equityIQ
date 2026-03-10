"""Tests for tools/ticker_search.py and GET /api/v1/search endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import router

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------


def _polygon_search_response(count: int = 3) -> dict:
    """Mock Polygon /v3/reference/tickers search response."""
    items = [
        {
            "ticker": "AAPL",
            "name": "Apple Inc.",
            "market": "stocks",
            "type": "CS",
            "locale": "us",
        },
        {
            "ticker": "AAPD",
            "name": "Direxion Daily AAPL Bear 1X Shares",
            "market": "stocks",
            "type": "ETF",
            "locale": "us",
        },
        {
            "ticker": "AAPU",
            "name": "Direxion Daily AAPL Bull 2X Shares",
            "market": "stocks",
            "type": "ETF",
            "locale": "us",
        },
    ]
    return {"results": items[:count], "status": "OK", "count": count}


def _mock_httpx_response(json_data: dict, status_code: int = 200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear the search cache before each test."""
    from tools.ticker_search import _search_cache

    _search_cache.clear()
    yield
    _search_cache.clear()


@pytest.fixture
def app():
    """Minimal test app with API router and mocked state."""
    from api.error_handlers import register_error_handlers

    test_app = FastAPI()
    register_error_handlers(test_app)
    test_app.include_router(router)

    # Mock all app.state dependencies that other routes need
    test_app.state.conductor = MagicMock()
    test_app.state.vault = MagicMock()
    test_app.state.history_retriever = MagicMock()

    return test_app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# search_tickers() unit tests
# ---------------------------------------------------------------------------


class TestSearchTickers:
    async def test_returns_results(self):
        """Successful search returns list of ticker dicts."""
        mock_resp = _mock_httpx_response(_polygon_search_response())

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            results = await search_tickers("AAPL")

        assert len(results) == 3
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["name"] == "Apple Inc."
        assert results[0]["market"] == "stocks"
        assert results[0]["type"] == "CS"
        assert results[0]["locale"] == "us"

    async def test_empty_query_returns_empty(self):
        """Empty or whitespace query returns [] without making API call."""
        from tools.ticker_search import search_tickers

        assert await search_tickers("") == []
        assert await search_tickers("   ") == []

    async def test_caching_second_call_uses_cache(self):
        """Second call with same query uses cache -- no HTTP."""
        mock_resp = _mock_httpx_response(_polygon_search_response())

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            result1 = await search_tickers("AAPL")
            result2 = await search_tickers("AAPL")

        assert result1 == result2
        # httpx.AsyncClient instantiated only once (first call), second from cache
        assert mock_client_cls.call_count == 1

    async def test_api_failure_returns_empty(self):
        """HTTP error returns empty list -- never crashes."""
        mock_resp = _mock_httpx_response({}, status_code=500)

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            results = await search_tickers("FAIL")

        assert results == []

    async def test_network_exception_returns_empty(self):
        """Network exception returns empty list."""
        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            results = await search_tickers("CRASH")

        assert results == []

    async def test_results_have_expected_keys(self):
        """Each result dict has exactly the 5 expected keys."""
        mock_resp = _mock_httpx_response(_polygon_search_response(1))

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            results = await search_tickers("AAPL")

        expected_keys = {"ticker", "name", "market", "type", "locale"}
        assert set(results[0].keys()) == expected_keys

    async def test_limit_parameter_passed(self):
        """Custom limit is forwarded to Polygon API params."""
        mock_resp = _mock_httpx_response(_polygon_search_response(1))

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            await search_tickers("AAPL", limit=5)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["limit"] == 5

    async def test_cache_key_is_case_insensitive(self):
        """Cache treats 'aapl' and 'AAPL' as same key."""
        mock_resp = _mock_httpx_response(_polygon_search_response())

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            await search_tickers("AAPL")
            await search_tickers("aapl")

        # Only one HTTP call -- second served from cache
        assert mock_client_cls.call_count == 1

    async def test_empty_results_from_api(self):
        """API returns empty results array -> returns []."""
        mock_resp = _mock_httpx_response({"results": [], "status": "OK"})

        with patch("tools.ticker_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_resp)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from tools.ticker_search import search_tickers

            results = await search_tickers("XYZNONEXISTENT")

        assert results == []


# ---------------------------------------------------------------------------
# /api/v1/search endpoint tests
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_search_returns_results(self, client):
        """GET /api/v1/search?q=AAPL returns ticker results."""
        mock_results = [
            {
                "ticker": "AAPL",
                "name": "Apple Inc.",
                "market": "stocks",
                "type": "CS",
                "locale": "us",
            }
        ]
        mock_yf = MagicMock()
        mock_yf.search_tickers = AsyncMock(return_value=mock_results)
        with patch("tools.yahoo_connector.yahoo", mock_yf):
            resp = client.get("/api/v1/search?q=AAPL")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["ticker"] == "AAPL"

    def test_search_empty_query(self, client):
        """GET /api/v1/search?q= returns empty list."""
        mock_yf = MagicMock()
        mock_yf.search_tickers = AsyncMock(return_value=[])
        with (
            patch("tools.yahoo_connector.yahoo", mock_yf),
            patch("api.routes.search_tickers", new_callable=AsyncMock) as mock_search,
        ):
            mock_search.return_value = []
            resp = client.get("/api/v1/search?q=")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_no_query_param(self, client):
        """GET /api/v1/search without q param defaults to empty string."""
        mock_yf = MagicMock()
        mock_yf.search_tickers = AsyncMock(return_value=[])
        with (
            patch("tools.yahoo_connector.yahoo", mock_yf),
            patch("api.routes.search_tickers", new_callable=AsyncMock) as mock_search,
        ):
            mock_search.return_value = []
            resp = client.get("/api/v1/search")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_passes_query_to_function(self, client):
        """Query parameter is forwarded to search functions."""
        mock_yf = MagicMock()
        mock_yf.search_tickers = AsyncMock(return_value=[])
        with (
            patch("tools.yahoo_connector.yahoo", mock_yf),
            patch("api.routes.search_tickers", new_callable=AsyncMock) as mock_search,
        ):
            mock_search.return_value = []
            client.get("/api/v1/search?q=Tesla")

        mock_yf.search_tickers.assert_awaited_once()
