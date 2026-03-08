"""Tests for tools/fred_connector.py -- FRED API async wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fred_response(series_id: str, observations: list[dict]) -> httpx.Response:
    """Build a fake FRED JSON response."""
    return httpx.Response(
        200,
        json={"observations": observations},
        request=httpx.Request("GET", f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}"),
    )


def _fred_error_response() -> httpx.Response:
    return httpx.Response(
        500,
        json={"error": "server error"},
        request=httpx.Request("GET", "https://api.stlouisfed.org/fred/series/observations"),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def connector():
    """Create a FredConnector with a fake API key."""
    from config.settings import Settings

    s = Settings(FRED_API_KEY="test-key-123")
    from tools.fred_connector import FredConnector

    return FredConnector(settings=s)


# ---------------------------------------------------------------------------
# Test: get_macro_indicators -- success
# ---------------------------------------------------------------------------

class TestGetMacroIndicatorsSuccess:
    @pytest.mark.asyncio
    async def test_returns_all_keys(self, connector):
        """Successful call returns all 5 keys."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()

        assert "gdp_growth" in result
        assert "inflation_rate" in result
        assert "fed_funds_rate" in result
        assert "unemployment_rate" in result
        assert "macro_regime" in result

    @pytest.mark.asyncio
    async def test_gdp_growth_calculation(self, connector):
        """GDP growth is computed as % change from last 2 observations."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()

        # (25000 - 24000) / 24000 * 100 = 4.166...
        assert result["gdp_growth"] == pytest.approx(4.1667, rel=1e-2)

    @pytest.mark.asyncio
    async def test_inflation_rate_calculation(self, connector):
        """Inflation rate computed as % change from last 2 CPI observations."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()

        # (315 - 305) / 305 * 100 = 3.2787...
        assert result["inflation_rate"] == pytest.approx(3.2787, rel=1e-2)

    @pytest.mark.asyncio
    async def test_fed_funds_rate_direct(self, connector):
        """Fed funds rate is extracted directly as float."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()
        assert result["fed_funds_rate"] == pytest.approx(5.33)

    @pytest.mark.asyncio
    async def test_unemployment_rate_direct(self, connector):
        """Unemployment rate is extracted directly as float."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()
        assert result["unemployment_rate"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Test: partial and total failure
# ---------------------------------------------------------------------------

class TestMacroIndicatorsFailures:
    @pytest.mark.asyncio
    async def test_partial_failure(self, connector):
        """If one series fails, others still returned, failed one is None."""
        responses = {
            "GDP": _fred_error_response(),  # GDP fails
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()

        assert result["gdp_growth"] is None
        assert result["fed_funds_rate"] == pytest.approx(5.33)
        assert result["unemployment_rate"] == pytest.approx(4.0)

    @pytest.mark.asyncio
    async def test_total_failure(self, connector):
        """If all series fail, return {}."""
        async def mock_get(url, **kwargs):
            raise httpx.ConnectError("connection refused")

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()
        assert result == {}

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self, connector):
        """Any exception in _fetch_series returns empty list."""
        async def mock_get(url, **kwargs):
            raise httpx.TimeoutException("timeout")

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()
        assert result == {}


# ---------------------------------------------------------------------------
# Test: FRED missing value "."
# ---------------------------------------------------------------------------

class TestFredMissingValues:
    @pytest.mark.asyncio
    async def test_dot_value_treated_as_none(self, connector):
        """FRED returns '.' for missing data -- should be treated as None."""
        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "."},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "."},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector.get_macro_indicators()

        assert result["gdp_growth"] is None
        assert result["fed_funds_rate"] is None
        assert result["unemployment_rate"] == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Test: regime classification
# ---------------------------------------------------------------------------

class TestClassifyRegime:
    def test_expansion(self, connector):
        assert connector._classify_regime(3.0, 2.5, 3.5) == "expansion"

    def test_contraction(self, connector):
        assert connector._classify_regime(-1.0, 2.0, 5.0) == "contraction"

    def test_stagflation(self, connector):
        assert connector._classify_regime(1.5, 5.0, 6.0) == "stagflation"

    def test_recovery(self, connector):
        assert connector._classify_regime(1.5, 3.0, 4.5) == "recovery"

    def test_none_insufficient_data(self, connector):
        assert connector._classify_regime(None, None, None) is None

    def test_none_partial_data(self, connector):
        assert connector._classify_regime(None, 3.0, 4.0) is None

    def test_contraction_takes_priority(self, connector):
        """Contraction (gdp < 0) overrides stagflation check."""
        assert connector._classify_regime(-0.5, 5.0, 6.0) == "contraction"


# ---------------------------------------------------------------------------
# Test: cache hit
# ---------------------------------------------------------------------------

class TestCacheHit:
    @pytest.mark.asyncio
    async def test_cache_prevents_duplicate_requests(self, connector):
        """Second call to get_macro_indicators should use cache."""
        call_count = 0

        responses = {
            "GDP": _fred_response("GDP", [
                {"date": "2024-01-01", "value": "25000.0"},
                {"date": "2023-10-01", "value": "24000.0"},
            ]),
            "CPIAUCSL": _fred_response("CPIAUCSL", [
                {"date": "2024-06-01", "value": "315.0"},
                {"date": "2023-06-01", "value": "305.0"},
            ]),
            "FEDFUNDS": _fred_response("FEDFUNDS", [
                {"date": "2024-06-01", "value": "5.33"},
            ]),
            "UNRATE": _fred_response("UNRATE", [
                {"date": "2024-06-01", "value": "4.0"},
            ]),
        }

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            params = kwargs.get("params", {})
            series_id = params.get("series_id", "")
            return responses.get(series_id, _fred_error_response())

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result1 = await connector.get_macro_indicators()
        first_call_count = call_count

        result2 = await connector.get_macro_indicators()

        # Second call should not make any new HTTP requests
        assert call_count == first_call_count
        assert result1 == result2


# ---------------------------------------------------------------------------
# Test: settings injection
# ---------------------------------------------------------------------------

class TestSettingsInjection:
    def test_api_key_from_settings(self):
        from config.settings import Settings
        from tools.fred_connector import FredConnector

        s = Settings(FRED_API_KEY="my-test-key")
        conn = FredConnector(settings=s)
        assert conn.api_key == "my-test-key"

    def test_default_settings_fallback(self):
        from tools.fred_connector import FredConnector

        with patch("tools.fred_connector.get_settings") as mock_settings:
            from config.settings import Settings

            mock_settings.return_value = Settings(FRED_API_KEY="default-key")
            conn = FredConnector()
            assert conn.api_key == "default-key"


# ---------------------------------------------------------------------------
# Test: module singleton
# ---------------------------------------------------------------------------

class TestModuleSingleton:
    def test_fred_singleton_importable(self):
        from tools.fred_connector import fred

        assert fred is not None
        from tools.fred_connector import FredConnector

        assert isinstance(fred, FredConnector)


# ---------------------------------------------------------------------------
# Test: close method
# ---------------------------------------------------------------------------

class TestCloseMethod:
    @pytest.mark.asyncio
    async def test_close_calls_aclose(self, connector):
        connector.client = AsyncMock()
        await connector.close()
        connector.client.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Test: _fetch_series
# ---------------------------------------------------------------------------

class TestFetchSeries:
    @pytest.mark.asyncio
    async def test_fetch_series_returns_observations(self, connector):
        response = _fred_response("FEDFUNDS", [
            {"date": "2024-06-01", "value": "5.33"},
        ])

        async def mock_get(url, **kwargs):
            return response

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector._fetch_series("FEDFUNDS")
        assert len(result) == 1
        assert result[0]["value"] == "5.33"

    @pytest.mark.asyncio
    async def test_fetch_series_error_returns_empty(self, connector):
        async def mock_get(url, **kwargs):
            raise httpx.TimeoutException("timeout")

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector._fetch_series("FEDFUNDS")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_series_non_200_returns_empty(self, connector):
        async def mock_get(url, **kwargs):
            return _fred_error_response()

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        result = await connector._fetch_series("FEDFUNDS")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_series_caches_result(self, connector):
        call_count = 0
        response = _fred_response("FEDFUNDS", [
            {"date": "2024-06-01", "value": "5.33"},
        ])

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return response

        connector.client = AsyncMock()
        connector.client.get = mock_get
        connector.client.aclose = AsyncMock()

        await connector._fetch_series("FEDFUNDS")
        await connector._fetch_series("FEDFUNDS")

        assert call_count == 1


# ---------------------------------------------------------------------------
# Test: connector attributes
# ---------------------------------------------------------------------------

class TestConnectorAttributes:
    def test_base_url(self, connector):
        assert connector.base_url == "https://api.stlouisfed.org"

    def test_cache_ttl(self, connector):
        assert connector.cache.ttl == 3600

    def test_cache_maxsize(self, connector):
        assert connector.cache.maxsize == 64

    def test_series_map(self, connector):
        assert "gdp_growth" in connector.SERIES_MAP
        assert "inflation_rate" in connector.SERIES_MAP
        assert "fed_funds_rate" in connector.SERIES_MAP
        assert "unemployment_rate" in connector.SERIES_MAP
        assert connector.SERIES_MAP["gdp_growth"] == "GDP"
        assert connector.SERIES_MAP["inflation_rate"] == "CPIAUCSL"
        assert connector.SERIES_MAP["fed_funds_rate"] == "FEDFUNDS"
        assert connector.SERIES_MAP["unemployment_rate"] == "UNRATE"
