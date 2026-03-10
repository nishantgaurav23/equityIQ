"""Tests for Zerodha Kite Connect integration (S17.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from integrations.zerodha import (
    ZerodhaClient,
    ZerodhaHolding,
    ZerodhaPortfolio,
    ZerodhaPosition,
    map_equityiq_to_zerodha,
    map_zerodha_to_equityiq,
)


def _mock_response(status_code: int, json_data: dict) -> httpx.Response:
    """Create an httpx.Response with a dummy request attached (needed for raise_for_status)."""
    resp = httpx.Response(status_code, json=json_data)
    resp._request = httpx.Request("GET", "https://api.kite.trade/test")
    return resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_HOLDINGS_RESPONSE = {
    "status": "success",
    "data": [
        {
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "quantity": 10,
            "average_price": 2450.50,
            "last_price": 2520.00,
            "pnl": 695.00,
            "day_change_percentage": 1.2,
        },
        {
            "tradingsymbol": "TCS",
            "exchange": "BSE",
            "quantity": 5,
            "average_price": 3800.00,
            "last_price": 3750.00,
            "pnl": -250.00,
            "day_change_percentage": -0.5,
        },
        {
            "tradingsymbol": "INFY",
            "exchange": "NSE",
            "quantity": 20,
            "average_price": 1500.00,
            "last_price": 1580.00,
            "pnl": 1600.00,
            "day_change_percentage": 0.8,
        },
    ],
}

SAMPLE_POSITIONS_RESPONSE = {
    "status": "success",
    "data": {
        "net": [
            {
                "tradingsymbol": "SBIN",
                "exchange": "NSE",
                "product": "CNC",
                "quantity": 50,
                "buy_price": 620.00,
                "sell_price": 0.0,
                "pnl": 500.00,
            },
        ],
        "day": [
            {
                "tradingsymbol": "HDFCBANK",
                "exchange": "NSE",
                "product": "MIS",
                "quantity": 10,
                "buy_price": 1680.00,
                "sell_price": 1700.00,
                "pnl": 200.00,
            },
        ],
    },
}

SAMPLE_TOKEN_RESPONSE = {
    "status": "success",
    "data": {
        "access_token": "abc123token",
        "user_id": "ZR1234",
        "user_name": "Test User",
    },
}


@pytest.fixture
def zerodha_settings():
    """Mock settings for Zerodha."""
    with patch("integrations.zerodha.get_settings") as mock:
        settings = mock.return_value
        settings.ZERODHA_API_KEY = "test_api_key"
        settings.ZERODHA_API_SECRET = "test_api_secret"
        settings.ZERODHA_REDIRECT_URL = "http://localhost:8000/api/v1/zerodha/callback"
        yield settings


@pytest_asyncio.fixture
async def client(zerodha_settings):
    """Create a ZerodhaClient with mocked settings."""
    c = ZerodhaClient()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Symbol Mapping Tests
# ---------------------------------------------------------------------------


class TestSymbolMapping:
    def test_nse_to_equityiq(self):
        assert map_zerodha_to_equityiq("RELIANCE", "NSE") == "RELIANCE.NS"

    def test_bse_to_equityiq(self):
        assert map_zerodha_to_equityiq("TCS", "BSE") == "TCS.BO"

    def test_unknown_exchange_returns_empty(self):
        assert map_zerodha_to_equityiq("AAPL", "NASDAQ") == ""

    def test_futures_skipped(self):
        assert map_zerodha_to_equityiq("RELIANCE23JUNFUT", "NSE") == ""

    def test_options_skipped(self):
        assert map_zerodha_to_equityiq("NIFTY23JUN18000CE", "NSE") == ""

    def test_nifty_skipped(self):
        assert map_zerodha_to_equityiq("NIFTY 50", "NSE") == ""

    def test_banknifty_skipped(self):
        assert map_zerodha_to_equityiq("BANKNIFTY", "NSE") == ""

    def test_equityiq_to_zerodha_ns(self):
        assert map_equityiq_to_zerodha("RELIANCE.NS") == ("RELIANCE", "NSE")

    def test_equityiq_to_zerodha_bo(self):
        assert map_equityiq_to_zerodha("TCS.BO") == ("TCS", "BSE")

    def test_equityiq_to_zerodha_unknown(self):
        assert map_equityiq_to_zerodha("AAPL") == ("", "")

    def test_whitespace_handling(self):
        assert map_zerodha_to_equityiq("  INFY  ", "  NSE  ") == "INFY.NS"
        assert map_equityiq_to_zerodha("  INFY.NS  ") == ("INFY", "NSE")

    def test_case_insensitive_exchange(self):
        assert map_zerodha_to_equityiq("RELIANCE", "nse") == "RELIANCE.NS"


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------


class TestDataModels:
    def test_holding_creation(self):
        h = ZerodhaHolding(
            tradingsymbol="RELIANCE",
            exchange="NSE",
            quantity=10,
            average_price=2450.0,
            last_price=2520.0,
            pnl=700.0,
        )
        assert h.tradingsymbol == "RELIANCE"
        assert h.day_change_percentage == 0.0  # default

    def test_holding_none_day_change(self):
        h = ZerodhaHolding(
            tradingsymbol="TCS",
            exchange="BSE",
            quantity=5,
            average_price=3800.0,
            last_price=3750.0,
            pnl=-250.0,
            day_change_percentage=None,
        )
        assert h.day_change_percentage == 0.0

    def test_position_creation(self):
        p = ZerodhaPosition(
            tradingsymbol="SBIN",
            exchange="NSE",
            product="CNC",
            quantity=50,
            buy_price=620.0,
            sell_price=0.0,
            pnl=500.0,
        )
        assert p.product == "CNC"

    def test_portfolio_creation(self):
        port = ZerodhaPortfolio(
            holdings=[],
            positions=[],
            total_invested=0.0,
            current_value=0.0,
            total_pnl=0.0,
            total_pnl_percentage=0.0,
            day_pnl=0.0,
        )
        assert port.equityiq_tickers == []
        assert port.connected_at is not None


# ---------------------------------------------------------------------------
# OAuth2 Flow Tests
# ---------------------------------------------------------------------------


class TestOAuth2:
    def test_login_url(self, client):
        url = client.get_login_url()
        assert "kite.zerodha.com/connect/login" in url
        assert "api_key=test_api_key" in url

    @pytest.mark.asyncio
    async def test_exchange_token_success(self, client):
        mock_resp = _mock_response(200, SAMPLE_TOKEN_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            result = await client.exchange_request_token("test_request_token")
            assert result["access_token"] == "abc123token"
            assert result["user_id"] == "ZR1234"

    @pytest.mark.asyncio
    async def test_exchange_token_expired(self, client):
        mock_resp = _mock_response(403, {"message": "Token expired"})
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            with pytest.raises(ValueError, match="Invalid or expired"):
                await client.exchange_request_token("bad_token")

    @pytest.mark.asyncio
    async def test_exchange_token_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_get.return_value = mock_http

            with pytest.raises(ValueError, match="Network error"):
                await client.exchange_request_token("test_token")


# ---------------------------------------------------------------------------
# Holdings Tests
# ---------------------------------------------------------------------------


class TestHoldings:
    @pytest.mark.asyncio
    async def test_get_holdings_success(self, client):
        mock_resp = _mock_response(200, SAMPLE_HOLDINGS_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            holdings = await client.get_holdings("test_token")
            assert len(holdings) == 3
            assert holdings[0].tradingsymbol == "RELIANCE"
            assert holdings[0].equityiq_ticker == "RELIANCE.NS"
            assert holdings[1].equityiq_ticker == "TCS.BO"
            assert holdings[2].equityiq_ticker == "INFY.NS"

    @pytest.mark.asyncio
    async def test_get_holdings_expired_token(self, client):
        mock_resp = _mock_response(403, {"message": "Token expired"})
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            with pytest.raises(PermissionError):
                await client.get_holdings("expired_token")

    @pytest.mark.asyncio
    async def test_get_holdings_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_get.return_value = mock_http

            holdings = await client.get_holdings("test_token")
            assert holdings == []  # graceful degradation

    @pytest.mark.asyncio
    async def test_holdings_cached(self, client):
        mock_resp = _mock_response(200, SAMPLE_HOLDINGS_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            h1 = await client.get_holdings("test_token")
            h2 = await client.get_holdings("test_token")
            assert h1 == h2
            # Only called once due to cache
            assert mock_http.get.call_count == 1


# ---------------------------------------------------------------------------
# Positions Tests
# ---------------------------------------------------------------------------


class TestPositions:
    @pytest.mark.asyncio
    async def test_get_positions_success(self, client):
        mock_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            positions = await client.get_positions("test_token")
            assert len(positions) == 2
            assert positions[0].tradingsymbol == "SBIN"
            assert positions[0].equityiq_ticker == "SBIN.NS"
            assert positions[1].tradingsymbol == "HDFCBANK"
            assert positions[1].product == "MIS"

    @pytest.mark.asyncio
    async def test_get_positions_expired_token(self, client):
        mock_resp = _mock_response(403, {"message": "Token expired"})
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            with pytest.raises(PermissionError):
                await client.get_positions("expired_token")

    @pytest.mark.asyncio
    async def test_get_positions_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_get.return_value = mock_http

            positions = await client.get_positions("test_token")
            assert positions == []


# ---------------------------------------------------------------------------
# Portfolio Summary Tests
# ---------------------------------------------------------------------------


class TestPortfolioSummary:
    @pytest.mark.asyncio
    async def test_portfolio_summary(self, client):
        holdings_resp = _mock_response(200, SAMPLE_HOLDINGS_RESPONSE)
        positions_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "holdings" in url:
                return holdings_resp
            return positions_resp

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary("test_token")

            assert len(portfolio.holdings) == 3
            assert len(portfolio.positions) == 2
            assert portfolio.total_invested > 0
            assert portfolio.current_value > 0
            # RELIANCE.NS, TCS.BO, INFY.NS from holdings + SBIN.NS, HDFCBANK.NS from positions
            assert "RELIANCE.NS" in portfolio.equityiq_tickers
            assert "TCS.BO" in portfolio.equityiq_tickers
            assert "SBIN.NS" in portfolio.equityiq_tickers
            assert len(portfolio.equityiq_tickers) == 5

    @pytest.mark.asyncio
    async def test_portfolio_pnl_calculation(self, client):
        holdings_resp = _mock_response(200, SAMPLE_HOLDINGS_RESPONSE)
        positions_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)

        async def mock_get(url, **kwargs):
            if "holdings" in url:
                return holdings_resp
            return positions_resp

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary("test_token")

            # total_invested = 10*2450.50 + 5*3800 + 20*1500 = 24505 + 19000 + 30000 = 73505
            assert portfolio.total_invested == 73505.0
            # current_value = 10*2520 + 5*3750 + 20*1580 = 25200 + 18750 + 31600 = 75550
            assert portfolio.current_value == 75550.0
            # total_pnl = 695 + (-250) + 1600 = 2045
            assert portfolio.total_pnl == 2045.0

    @pytest.mark.asyncio
    async def test_empty_portfolio(self, client):
        empty_holdings = {"status": "success", "data": []}
        empty_positions = {"status": "success", "data": {"net": [], "day": []}}

        async def mock_get(url, **kwargs):
            if "holdings" in url:
                return _mock_response(200, empty_holdings)
            return _mock_response(200, empty_positions)

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary("test_token")
            assert portfolio.total_invested == 0
            assert portfolio.total_pnl_percentage == 0
            assert portfolio.equityiq_tickers == []


# ---------------------------------------------------------------------------
# Settings Tests
# ---------------------------------------------------------------------------


class TestSettings:
    def test_zerodha_settings_exist(self):
        from config.settings import Settings

        s = Settings(
            ZERODHA_API_KEY="key",
            ZERODHA_API_SECRET="secret",
        )
        assert s.ZERODHA_API_KEY == "key"
        assert s.ZERODHA_API_SECRET == "secret"
        assert "callback" in s.ZERODHA_REDIRECT_URL

    def test_zerodha_settings_default_empty(self):
        from config.settings import Settings

        s = Settings()
        assert s.ZERODHA_API_KEY == ""
        assert s.ZERODHA_API_SECRET == ""


# ---------------------------------------------------------------------------
# Route Tests (FastAPI TestClient)
# ---------------------------------------------------------------------------


class TestRoutes:
    @pytest.fixture
    def test_app(self):
        """Create a minimal test app with Zerodha routes."""
        from unittest.mock import MagicMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.zerodha_routes import router

        app = FastAPI()
        app.include_router(router)

        # Mock app state
        app.state.conductor = MagicMock()
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=None)

        return TestClient(app)

    def test_login_endpoint(self, test_app, zerodha_settings):
        resp = test_app.get("/api/v1/zerodha/login")
        assert resp.status_code == 200
        data = resp.json()
        assert "login_url" in data
        assert "kite.zerodha.com" in data["login_url"]

    def test_holdings_no_token(self, test_app):
        resp = test_app.get("/api/v1/zerodha/holdings")
        assert resp.status_code == 422  # Missing required header

    def test_positions_no_token(self, test_app):
        resp = test_app.get("/api/v1/zerodha/positions")
        assert resp.status_code == 422

    def test_portfolio_no_token(self, test_app):
        resp = test_app.get("/api/v1/zerodha/portfolio")
        assert resp.status_code == 422

    def test_holdings_with_mock_token(self, test_app, zerodha_settings):
        with patch(
            "api.zerodha_routes.ZerodhaClient.get_holdings",
            new_callable=AsyncMock,
            return_value=[
                ZerodhaHolding(
                    tradingsymbol="RELIANCE",
                    exchange="NSE",
                    quantity=10,
                    average_price=2450.0,
                    last_price=2520.0,
                    pnl=700.0,
                    equityiq_ticker="RELIANCE.NS",
                )
            ],
        ):
            resp = test_app.get(
                "/api/v1/zerodha/holdings",
                headers={"X-Zerodha-Token": "test_token"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["tradingsymbol"] == "RELIANCE"

    def test_callback_endpoint(self, test_app, zerodha_settings):
        with patch(
            "api.zerodha_routes.ZerodhaClient.exchange_request_token",
            new_callable=AsyncMock,
            return_value={"access_token": "abc123", "user_id": "ZR1234"},
        ):
            resp = test_app.get("/api/v1/zerodha/callback?request_token=test_req_token")
            assert resp.status_code == 200
            data = resp.json()
            assert data["access_token"] == "abc123"
            assert data["user_id"] == "ZR1234"

    def test_callback_invalid_token(self, test_app, zerodha_settings):
        with patch(
            "api.zerodha_routes.ZerodhaClient.exchange_request_token",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid or expired request token"),
        ):
            resp = test_app.get("/api/v1/zerodha/callback?request_token=bad_token")
            assert resp.status_code == 401
