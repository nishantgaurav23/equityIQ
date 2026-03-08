"""Tests for tools/polygon_connector.py -- Polygon.io async wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from config.settings import Settings

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings():
    """Settings with a test API key."""
    return Settings(POLYGON_API_KEY="test-key-123")


@pytest.fixture
def connector(mock_settings):
    """Fresh PolygonConnector with injected settings."""
    from tools.polygon_connector import PolygonConnector

    return PolygonConnector(settings=mock_settings)


# ---------------------------------------------------------------------------
# Polygon API mock response factories
# ---------------------------------------------------------------------------

def _fundamentals_response():
    """Mock response for /vX/reference/financials."""
    return {
        "results": [
            {
                "pe_ratio": 25.3,
                "pb_ratio": 8.1,
                "financials": {
                    "income_statement": {
                        "revenues": {"value": 394328000000},
                    },
                    "balance_sheet": {
                        "debt_to_equity_ratio": {"value": 1.87},
                    },
                    "cash_flow_statement": {
                        "free_cash_flow": {"value": 111443000000},
                    },
                },
            }
        ],
        "status": "OK",
    }


def _price_history_response():
    """Mock response for /v2/aggs/ticker/.../range/1/day/."""
    return {
        "results": [
            {"c": 150.0, "v": 1000000, "t": 1704067200000},  # 2024-01-01
            {"c": 152.5, "v": 1100000, "t": 1704153600000},  # 2024-01-02
            {"c": 148.0, "v": 900000, "t": 1704240000000},   # 2024-01-03
        ],
        "resultsCount": 3,
        "status": "OK",
    }


def _news_response():
    """Mock response for /v2/reference/news."""
    return {
        "results": [
            {"title": "AAPL hits record high", "published_utc": "2024-01-15T10:00:00Z"},
            {"title": "Apple Q1 earnings beat", "published_utc": "2024-01-14T08:00:00Z"},
        ],
        "status": "OK",
    }


def _mock_httpx_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


# ---------------------------------------------------------------------------
# get_fundamentals tests
# ---------------------------------------------------------------------------

class TestGetFundamentals:
    async def test_success(self, connector):
        """Successful fundamentals fetch returns expected keys."""
        mock_resp = _mock_httpx_response(_fundamentals_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_fundamentals("AAPL")

        assert "pe_ratio" in result
        assert "pb_ratio" in result
        assert "revenue_growth" in result
        assert "debt_to_equity" in result
        assert "fcf_yield" in result
        assert result["pe_ratio"] == 25.3

    async def test_empty_results(self, connector):
        """Empty results array returns {}."""
        mock_resp = _mock_httpx_response({"results": [], "status": "OK"})
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_fundamentals("INVALID")
        assert result == {}

    async def test_http_error(self, connector):
        """Non-200 status returns {}."""
        mock_resp = _mock_httpx_response({}, status_code=403)
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_fundamentals("AAPL")
        assert result == {}

    async def test_exception(self, connector):
        """Network exception returns {} -- never crashes."""
        connector.client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))

        result = await connector.get_fundamentals("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# get_price_history tests
# ---------------------------------------------------------------------------

class TestGetPriceHistory:
    async def test_success(self, connector):
        """Successful price history returns prices, volumes, dates."""
        mock_resp = _mock_httpx_response(_price_history_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_price_history("AAPL", days=90)

        assert "prices" in result
        assert "volumes" in result
        assert "dates" in result
        assert len(result["prices"]) == 3
        assert result["prices"][0] == 150.0
        assert result["volumes"][1] == 1100000

    async def test_empty_results(self, connector):
        """No results returns {}."""
        mock_resp = _mock_httpx_response({"results": [], "status": "OK"})
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_price_history("INVALID")
        assert result == {}

    async def test_missing_results_key(self, connector):
        """Response without 'results' key returns {}."""
        mock_resp = _mock_httpx_response({"status": "OK"})
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_price_history("AAPL")
        assert result == {}

    async def test_exception(self, connector):
        """Network exception returns {}."""
        connector.client.get = AsyncMock(side_effect=Exception("connection failed"))

        result = await connector.get_price_history("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# get_company_news tests
# ---------------------------------------------------------------------------

class TestGetCompanyNews:
    async def test_success(self, connector):
        """Successful news fetch returns headlines and articles."""
        mock_resp = _mock_httpx_response(_news_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_company_news("AAPL")

        assert "headlines" in result
        assert "articles" in result
        assert len(result["headlines"]) == 2
        assert result["headlines"][0] == "AAPL hits record high"
        assert result["articles"][0]["title"] == "AAPL hits record high"
        assert "published_utc" in result["articles"][0]

    async def test_empty_results(self, connector):
        """Empty results returns {}."""
        mock_resp = _mock_httpx_response({"results": [], "status": "OK"})
        connector.client.get = AsyncMock(return_value=mock_resp)

        result = await connector.get_company_news("INVALID")
        assert result == {}

    async def test_exception(self, connector):
        """Network exception returns {}."""
        connector.client.get = AsyncMock(side_effect=httpx.TimeoutException("slow"))

        result = await connector.get_company_news("AAPL")
        assert result == {}


# ---------------------------------------------------------------------------
# Caching tests
# ---------------------------------------------------------------------------

class TestCaching:
    async def test_cache_hit_fundamentals(self, connector):
        """Second call for same ticker serves from cache -- no HTTP."""
        mock_resp = _mock_httpx_response(_fundamentals_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        result1 = await connector.get_fundamentals("AAPL")
        result2 = await connector.get_fundamentals("AAPL")

        assert result1 == result2
        # HTTP called exactly once -- second served from cache
        connector.client.get.assert_awaited_once()

    async def test_cache_hit_price_history(self, connector):
        """Price history cache works."""
        mock_resp = _mock_httpx_response(_price_history_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        await connector.get_price_history("AAPL", days=90)
        await connector.get_price_history("AAPL", days=90)

        connector.client.get.assert_awaited_once()

    async def test_cache_miss_different_ticker(self, connector):
        """Different tickers are separate cache entries."""
        mock_resp = _mock_httpx_response(_fundamentals_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        await connector.get_fundamentals("AAPL")
        await connector.get_fundamentals("MSFT")

        assert connector.client.get.await_count == 2


# ---------------------------------------------------------------------------
# Settings injection tests
# ---------------------------------------------------------------------------

class TestSettingsInjection:
    async def test_api_key_in_request(self, connector):
        """API key from settings is passed in request params."""
        mock_resp = _mock_httpx_response(_fundamentals_response())
        connector.client.get = AsyncMock(return_value=mock_resp)

        await connector.get_fundamentals("AAPL")

        call_kwargs = connector.client.get.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["apiKey"] == "test-key-123"

    def test_default_settings_fallback(self):
        """Without explicit settings, falls back to get_settings()."""
        from tools.polygon_connector import PolygonConnector

        with patch("tools.polygon_connector.get_settings") as mock_gs:
            mock_gs.return_value = Settings(POLYGON_API_KEY="fallback-key")
            conn = PolygonConnector()
            assert conn.api_key == "fallback-key"


# ---------------------------------------------------------------------------
# Module singleton & close tests
# ---------------------------------------------------------------------------

class TestModuleSingleton:
    def test_singleton_importable(self):
        """Module-level 'polygon' singleton is importable."""
        from tools.polygon_connector import polygon

        assert polygon is not None
        assert hasattr(polygon, "get_fundamentals")
        assert hasattr(polygon, "get_price_history")
        assert hasattr(polygon, "get_company_news")

    def test_singleton_is_polygon_connector(self):
        """Singleton is an instance of PolygonConnector."""
        from tools.polygon_connector import PolygonConnector, polygon

        assert isinstance(polygon, PolygonConnector)


class TestClose:
    async def test_close_calls_aclose(self, connector):
        """close() calls the underlying httpx client aclose()."""
        connector.client = MagicMock()
        connector.client.aclose = AsyncMock()

        await connector.close()
        connector.client.aclose.assert_awaited_once()
