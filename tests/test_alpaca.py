"""Tests for Alpaca broker integration (S17.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from integrations.alpaca import (
    AlpacaAccount,
    AlpacaClient,
    AlpacaOrder,
    AlpacaPortfolio,
    AlpacaPosition,
    map_alpaca_to_equityiq,
    map_equityiq_to_alpaca,
)


def _mock_response(status_code: int, json_data: dict) -> httpx.Response:
    """Create an httpx.Response with a dummy request attached."""
    resp = httpx.Response(status_code, json=json_data)
    resp._request = httpx.Request("GET", "https://paper-api.alpaca.markets/test")
    return resp


# ---------------------------------------------------------------------------
# Sample API Responses
# ---------------------------------------------------------------------------

SAMPLE_ACCOUNT_RESPONSE = {
    "id": "acc-123",
    "buying_power": "50000.00",
    "portfolio_value": "125000.00",
    "cash": "50000.00",
    "equity": "125000.00",
    "last_equity": "124000.00",
    "daytrade_count": 2,
    "pattern_day_trader": False,
    "trading_blocked": False,
    "account_blocked": False,
}

SAMPLE_POSITIONS_RESPONSE = [
    {
        "symbol": "AAPL",
        "qty": "10",
        "avg_entry_price": "175.50",
        "current_price": "182.30",
        "market_value": "1823.00",
        "unrealized_pl": "68.00",
        "unrealized_plpc": "0.0387",
        "side": "long",
    },
    {
        "symbol": "MSFT",
        "qty": "5",
        "avg_entry_price": "380.00",
        "current_price": "395.20",
        "market_value": "1976.00",
        "unrealized_pl": "76.00",
        "unrealized_plpc": "0.04",
        "side": "long",
    },
    {
        "symbol": "TSLA",
        "qty": "3",
        "avg_entry_price": "250.00",
        "current_price": "242.50",
        "market_value": "727.50",
        "unrealized_pl": "-22.50",
        "unrealized_plpc": "-0.03",
        "side": "long",
    },
]

SAMPLE_ORDER_RESPONSE = {
    "id": "order-456",
    "symbol": "AAPL",
    "qty": "5",
    "side": "buy",
    "type": "market",
    "status": "new",
    "filled_qty": "0",
    "filled_avg_price": None,
    "submitted_at": "2026-03-10T10:30:00Z",
}


@pytest.fixture
def alpaca_settings():
    """Mock settings for Alpaca."""
    with patch("integrations.alpaca.get_settings") as mock:
        settings = mock.return_value
        settings.ALPACA_API_KEY = "test_api_key"
        settings.ALPACA_API_SECRET = "test_api_secret"
        settings.ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
        settings.ALPACA_DATA_URL = "https://data.alpaca.markets"
        settings.ALPACA_ALLOW_PAPER_TRADING = False
        yield settings


@pytest_asyncio.fixture
async def client(alpaca_settings):
    """Create an AlpacaClient with mocked settings."""
    c = AlpacaClient()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Symbol Mapping Tests
# ---------------------------------------------------------------------------


class TestSymbolMapping:
    def test_us_stock_passthrough(self):
        assert map_alpaca_to_equityiq("AAPL") == "AAPL"

    def test_us_stock_with_whitespace(self):
        assert map_alpaca_to_equityiq("  MSFT  ") == "MSFT"

    def test_class_b_shares(self):
        assert map_alpaca_to_equityiq("BRK.B") == "BRK-B"

    def test_empty_string(self):
        assert map_alpaca_to_equityiq("") == ""

    def test_equityiq_to_alpaca_us(self):
        assert map_equityiq_to_alpaca("AAPL") == "AAPL"

    def test_equityiq_to_alpaca_class_b(self):
        assert map_equityiq_to_alpaca("BRK-B") == "BRK.B"

    def test_equityiq_to_alpaca_indian_ns(self):
        assert map_equityiq_to_alpaca("RELIANCE.NS") == ""

    def test_equityiq_to_alpaca_indian_bo(self):
        assert map_equityiq_to_alpaca("TCS.BO") == ""

    def test_equityiq_to_alpaca_whitespace(self):
        assert map_equityiq_to_alpaca("  TSLA  ") == "TSLA"

    def test_equityiq_to_alpaca_empty(self):
        assert map_equityiq_to_alpaca("") == ""


# ---------------------------------------------------------------------------
# Data Model Tests
# ---------------------------------------------------------------------------


class TestDataModels:
    def test_position_creation(self):
        p = AlpacaPosition(
            symbol="AAPL",
            qty=10.0,
            avg_entry_price=175.50,
            current_price=182.30,
            market_value=1823.00,
            unrealized_pl=68.00,
            unrealized_plpc=0.0387,
            side="long",
        )
        assert p.symbol == "AAPL"
        assert p.equityiq_ticker == ""  # default

    def test_account_creation(self):
        a = AlpacaAccount(
            account_id="acc-123",
            buying_power=50000.0,
            portfolio_value=125000.0,
            cash=50000.0,
            equity=125000.0,
            last_equity=124000.0,
            day_trade_count=2,
            pattern_day_trader=False,
            trading_blocked=False,
            account_blocked=False,
        )
        assert a.account_id == "acc-123"
        assert a.buying_power == 50000.0

    def test_order_creation(self):
        o = AlpacaOrder(
            order_id="order-456",
            symbol="AAPL",
            qty=5.0,
            side="buy",
            order_type="market",
            status="new",
            submitted_at=datetime.now(timezone.utc),
        )
        assert o.filled_qty == 0.0
        assert o.filled_avg_price == 0.0

    def test_portfolio_creation(self):
        port = AlpacaPortfolio(
            positions=[],
            account=AlpacaAccount(
                account_id="acc-123",
                buying_power=50000.0,
                portfolio_value=125000.0,
                cash=50000.0,
                equity=125000.0,
                last_equity=124000.0,
                day_trade_count=0,
                pattern_day_trader=False,
                trading_blocked=False,
                account_blocked=False,
            ),
            portfolio_value=125000.0,
            buying_power=50000.0,
            total_unrealized_pl=0.0,
            total_unrealized_plpc=0.0,
            day_pl=0.0,
            equityiq_tickers=[],
        )
        assert port.equityiq_tickers == []
        assert port.connected_at is not None


# ---------------------------------------------------------------------------
# Authentication Tests
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_auth_headers(self, client):
        headers = client._auth_headers()
        assert headers["APCA-API-KEY-ID"] == "test_api_key"
        assert headers["APCA-API-SECRET-KEY"] == "test_api_secret"

    def test_is_paper_trading(self, client):
        assert client.is_paper_trading is True

    def test_is_live_trading(self, alpaca_settings):
        alpaca_settings.ALPACA_BASE_URL = "https://api.alpaca.markets"
        c = AlpacaClient()
        assert c.is_paper_trading is False


# ---------------------------------------------------------------------------
# Account Tests
# ---------------------------------------------------------------------------


class TestAccount:
    @pytest.mark.asyncio
    async def test_get_account_success(self, client):
        mock_resp = _mock_response(200, SAMPLE_ACCOUNT_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            account = await client.get_account()
            assert account.account_id == "acc-123"
            assert account.buying_power == 50000.0
            assert account.portfolio_value == 125000.0

    @pytest.mark.asyncio
    async def test_get_account_invalid_creds(self, client):
        mock_resp = _mock_response(401, {"message": "Invalid credentials"})
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            with pytest.raises(PermissionError, match="Invalid"):
                await client.get_account()

    @pytest.mark.asyncio
    async def test_get_account_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError, match="Network error"):
                await client.get_account()


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

            positions = await client.get_positions()
            assert len(positions) == 3
            assert positions[0].symbol == "AAPL"
            assert positions[0].equityiq_ticker == "AAPL"
            assert positions[1].equityiq_ticker == "MSFT"
            assert positions[2].equityiq_ticker == "TSLA"

    @pytest.mark.asyncio
    async def test_get_positions_invalid_creds(self, client):
        mock_resp = _mock_response(401, {"message": "Invalid credentials"})
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            with pytest.raises(PermissionError):
                await client.get_positions()

    @pytest.mark.asyncio
    async def test_get_positions_network_error(self, client):
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_get.return_value = mock_http

            positions = await client.get_positions()
            assert positions == []  # graceful degradation

    @pytest.mark.asyncio
    async def test_positions_cached(self, client):
        mock_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)
        with patch.object(client, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            p1 = await client.get_positions()
            p2 = await client.get_positions()
            assert p1 == p2
            assert mock_http.get.call_count == 1


# ---------------------------------------------------------------------------
# Portfolio Summary Tests
# ---------------------------------------------------------------------------


class TestPortfolioSummary:
    @pytest.mark.asyncio
    async def test_portfolio_summary(self, client):
        account_resp = _mock_response(200, SAMPLE_ACCOUNT_RESPONSE)
        positions_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "account" in url:
                return account_resp
            return positions_resp

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary()

            assert len(portfolio.positions) == 3
            assert portfolio.portfolio_value == 125000.0
            assert portfolio.buying_power == 50000.0
            assert "AAPL" in portfolio.equityiq_tickers
            assert "MSFT" in portfolio.equityiq_tickers
            assert "TSLA" in portfolio.equityiq_tickers
            assert len(portfolio.equityiq_tickers) == 3

    @pytest.mark.asyncio
    async def test_portfolio_pnl_calculation(self, client):
        account_resp = _mock_response(200, SAMPLE_ACCOUNT_RESPONSE)
        positions_resp = _mock_response(200, SAMPLE_POSITIONS_RESPONSE)

        async def mock_get(url, **kwargs):
            if "account" in url:
                return account_resp
            return positions_resp

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary()

            # total unrealized P&L = 68.00 + 76.00 + (-22.50) = 121.50
            assert portfolio.total_unrealized_pl == 121.50
            # day P&L = equity - last_equity = 125000 - 124000 = 1000
            assert portfolio.day_pl == 1000.0

    @pytest.mark.asyncio
    async def test_empty_portfolio(self, client):
        account_resp = _mock_response(200, SAMPLE_ACCOUNT_RESPONSE)
        positions_resp = _mock_response(200, [])

        async def mock_get(url, **kwargs):
            if "account" in url:
                return account_resp
            return positions_resp

        with patch.object(client, "_get_client") as mock_get_client:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=mock_get)
            mock_get_client.return_value = mock_http

            portfolio = await client.get_portfolio_summary()
            assert portfolio.total_unrealized_pl == 0.0
            assert portfolio.equityiq_tickers == []


# ---------------------------------------------------------------------------
# Paper Order Tests
# ---------------------------------------------------------------------------


class TestPaperOrders:
    @pytest.mark.asyncio
    async def test_paper_order_success(self, client, alpaca_settings):
        alpaca_settings.ALPACA_ALLOW_PAPER_TRADING = True
        c = AlpacaClient()
        mock_resp = _mock_response(200, SAMPLE_ORDER_RESPONSE)
        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(return_value=mock_resp)
            mock_get.return_value = mock_http

            order = await c.place_paper_order("AAPL", 5, "buy")
            assert order.order_id == "order-456"
            assert order.symbol == "AAPL"
            assert order.status == "new"
            await c.close()

    @pytest.mark.asyncio
    async def test_paper_order_blocked_when_disabled(self, client):
        # ALPACA_ALLOW_PAPER_TRADING is False by default in fixture
        with pytest.raises(PermissionError, match="Paper trading is not enabled"):
            await client.place_paper_order("AAPL", 5, "buy")

    @pytest.mark.asyncio
    async def test_paper_order_blocked_on_live(self, alpaca_settings):
        alpaca_settings.ALPACA_BASE_URL = "https://api.alpaca.markets"
        alpaca_settings.ALPACA_ALLOW_PAPER_TRADING = True
        c = AlpacaClient()
        with pytest.raises(PermissionError, match="Live trading is not allowed"):
            await c.place_paper_order("AAPL", 5, "buy")
        await c.close()

    @pytest.mark.asyncio
    async def test_paper_order_network_error(self, client, alpaca_settings):
        alpaca_settings.ALPACA_ALLOW_PAPER_TRADING = True
        c = AlpacaClient()
        with patch.object(c, "_get_client") as mock_get:
            mock_http = AsyncMock()
            mock_http.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))
            mock_get.return_value = mock_http

            with pytest.raises(ConnectionError):
                await c.place_paper_order("AAPL", 5, "buy")
            await c.close()


# ---------------------------------------------------------------------------
# Settings Tests
# ---------------------------------------------------------------------------


class TestSettings:
    def test_alpaca_settings_exist(self):
        from config.settings import Settings

        s = Settings(
            ALPACA_API_KEY="key",
            ALPACA_API_SECRET="secret",
        )
        assert s.ALPACA_API_KEY == "key"
        assert s.ALPACA_API_SECRET == "secret"
        assert "paper-api" in s.ALPACA_BASE_URL

    def test_alpaca_settings_default_empty(self):
        from config.settings import Settings

        s = Settings()
        assert s.ALPACA_API_KEY == ""
        assert s.ALPACA_API_SECRET == ""
        assert s.ALPACA_ALLOW_PAPER_TRADING is False


# ---------------------------------------------------------------------------
# Route Tests (FastAPI TestClient)
# ---------------------------------------------------------------------------


class TestRoutes:
    @pytest.fixture
    def test_app(self):
        """Create a minimal test app with Alpaca routes."""
        from unittest.mock import MagicMock

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.alpaca_routes import router

        app = FastAPI()
        app.include_router(router)

        # Mock app state
        app.state.conductor = MagicMock()
        app.state.conductor.analyze_portfolio = AsyncMock(return_value=None)

        return TestClient(app)

    def test_account_no_headers(self, test_app):
        resp = test_app.get("/api/v1/alpaca/account")
        assert resp.status_code == 422  # Missing required headers

    def test_positions_no_headers(self, test_app):
        resp = test_app.get("/api/v1/alpaca/positions")
        assert resp.status_code == 422

    def test_portfolio_no_headers(self, test_app):
        resp = test_app.get("/api/v1/alpaca/portfolio")
        assert resp.status_code == 422

    def test_positions_with_mock(self, test_app, alpaca_settings):
        with patch(
            "api.alpaca_routes.AlpacaClient.get_positions",
            new_callable=AsyncMock,
            return_value=[
                AlpacaPosition(
                    symbol="AAPL",
                    qty=10.0,
                    avg_entry_price=175.50,
                    current_price=182.30,
                    market_value=1823.00,
                    unrealized_pl=68.00,
                    unrealized_plpc=0.0387,
                    side="long",
                    equityiq_ticker="AAPL",
                )
            ],
        ):
            resp = test_app.get(
                "/api/v1/alpaca/positions",
                headers={
                    "X-Alpaca-Key": "test_key",
                    "X-Alpaca-Secret": "test_secret",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["symbol"] == "AAPL"

    def test_account_with_mock(self, test_app, alpaca_settings):
        with patch(
            "api.alpaca_routes.AlpacaClient.get_account",
            new_callable=AsyncMock,
            return_value=AlpacaAccount(
                account_id="acc-123",
                buying_power=50000.0,
                portfolio_value=125000.0,
                cash=50000.0,
                equity=125000.0,
                last_equity=124000.0,
                day_trade_count=2,
                pattern_day_trader=False,
                trading_blocked=False,
                account_blocked=False,
            ),
        ):
            resp = test_app.get(
                "/api/v1/alpaca/account",
                headers={
                    "X-Alpaca-Key": "test_key",
                    "X-Alpaca-Secret": "test_secret",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["account_id"] == "acc-123"

    def test_paper_order_no_headers(self, test_app):
        resp = test_app.post(
            "/api/v1/alpaca/paper-order",
            json={"symbol": "AAPL", "qty": 5, "side": "buy"},
        )
        assert resp.status_code == 422
