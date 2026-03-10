"""Tests for webhook alert system (S17.4)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from config.data_contracts import FinalVerdict

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_verdict(
    ticker: str = "AAPL", signal: str = "BUY", confidence: float = 0.72
) -> FinalVerdict:
    """Create a minimal FinalVerdict for testing."""
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        price_target=150.0,
        analyst_signals={"valuation": "BUY", "momentum": "HOLD"},
        risk_summary="Low risk",
        key_drivers=["Strong fundamentals"],
        session_id="test-session-001",
    )


@pytest_asyncio.fixture
async def alert_engine():
    """Create an AlertEngine with a temp DB."""
    from integrations.alerts import AlertEngine

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_alerts.db")
        engine = AlertEngine(db_path=db_path)
        await engine.initialize()
        yield engine
        await engine.close()


# ---------------------------------------------------------------------------
# Watchlist Management (FR-1)
# ---------------------------------------------------------------------------


class TestAddWatch:
    @pytest.mark.asyncio
    async def test_add_watch_creates_entry(self, alert_engine):
        entry = await alert_engine.add_watch("AAPL", "https://example.com/hook")
        assert entry.ticker == "AAPL"
        assert entry.webhook_url == "https://example.com/hook"
        assert entry.channel == "webhook"
        assert entry.active is True

    @pytest.mark.asyncio
    async def test_add_watch_duplicate_updates(self, alert_engine):
        await alert_engine.add_watch("AAPL", "https://example.com/hook")
        await alert_engine.add_watch("AAPL", "https://example.com/hook")
        # Should still be one entry
        watchlist = await alert_engine.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0].ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_add_watch_max_limit(self, alert_engine):
        """Exceeding max watchlist size raises ValueError."""
        # Temporarily set a small limit
        alert_engine._max_watchlist_size = 3
        await alert_engine.add_watch("AAPL", "https://example.com/1")
        await alert_engine.add_watch("MSFT", "https://example.com/2")
        await alert_engine.add_watch("GOOG", "https://example.com/3")
        with pytest.raises(ValueError, match="watchlist limit"):
            await alert_engine.add_watch("TSLA", "https://example.com/4")


class TestRemoveWatch:
    @pytest.mark.asyncio
    async def test_remove_watch(self, alert_engine):
        entry = await alert_engine.add_watch("AAPL", "https://example.com/hook")
        removed = await alert_engine.remove_watch(entry.id)
        assert removed is True
        watchlist = await alert_engine.get_watchlist()
        assert len(watchlist) == 0

    @pytest.mark.asyncio
    async def test_remove_watch_nonexistent(self, alert_engine):
        removed = await alert_engine.remove_watch(9999)
        assert removed is False


class TestGetWatchlist:
    @pytest.mark.asyncio
    async def test_get_watchlist_active_only(self, alert_engine):
        await alert_engine.add_watch("AAPL", "https://example.com/1")
        entry2 = await alert_engine.add_watch("MSFT", "https://example.com/2")
        await alert_engine.remove_watch(entry2.id)
        watchlist = await alert_engine.get_watchlist()
        assert len(watchlist) == 1
        assert watchlist[0].ticker == "AAPL"


# ---------------------------------------------------------------------------
# Signal Change Detection (FR-3)
# ---------------------------------------------------------------------------


class TestDetectChange:
    @pytest.mark.asyncio
    async def test_detect_change_upgrade(self, alert_engine):

        old = _make_verdict("AAPL", "HOLD", 0.55)
        new = _make_verdict("AAPL", "BUY", 0.72)
        change = alert_engine._detect_signal_change("AAPL", new, old)
        assert change.change_type == "upgrade"
        assert change.old_signal == "HOLD"
        assert change.new_signal == "BUY"

    @pytest.mark.asyncio
    async def test_detect_change_downgrade(self, alert_engine):
        old = _make_verdict("AAPL", "BUY", 0.72)
        new = _make_verdict("AAPL", "SELL", 0.65)
        change = alert_engine._detect_signal_change("AAPL", new, old)
        assert change.change_type == "downgrade"

    @pytest.mark.asyncio
    async def test_detect_change_no_change(self, alert_engine):
        old = _make_verdict("AAPL", "BUY", 0.72)
        new = _make_verdict("AAPL", "BUY", 0.73)
        change = alert_engine._detect_signal_change("AAPL", new, old)
        assert change.change_type == "no_change"

    @pytest.mark.asyncio
    async def test_detect_change_initial(self, alert_engine):
        new = _make_verdict("AAPL", "BUY", 0.72)
        change = alert_engine._detect_signal_change("AAPL", new, None)
        assert change.change_type == "initial"
        assert change.old_signal is None

    @pytest.mark.asyncio
    async def test_detect_change_confidence_shift(self, alert_engine):
        old = _make_verdict("AAPL", "BUY", 0.55)
        new = _make_verdict("AAPL", "BUY", 0.75)
        change = alert_engine._detect_signal_change("AAPL", new, old)
        assert change.change_type == "confidence_shift"


# ---------------------------------------------------------------------------
# Webhook Delivery (FR-4)
# ---------------------------------------------------------------------------


class TestDeliverWebhook:
    @pytest.mark.asyncio
    async def test_deliver_webhook_success(self, alert_engine):
        from integrations.alerts import SignalChange, WatchlistEntry

        change = SignalChange(
            ticker="AAPL",
            old_signal="HOLD",
            new_signal="BUY",
            old_confidence=0.55,
            new_confidence=0.72,
            change_type="upgrade",
        )
        entry = WatchlistEntry(
            id=1,
            ticker="AAPL",
            webhook_url="https://example.com/hook",
        )

        mock_resp = httpx.Response(200, json={"ok": True})
        mock_resp._request = httpx.Request("POST", "https://example.com/hook")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            result = await alert_engine.deliver_webhook(change, entry)
        assert result.success is True
        assert result.status_code == 200
        assert result.retries_used == 0

    @pytest.mark.asyncio
    async def test_deliver_webhook_retry_on_failure(self, alert_engine):
        from integrations.alerts import SignalChange, WatchlistEntry

        change = SignalChange(
            ticker="AAPL",
            old_signal="HOLD",
            new_signal="BUY",
            old_confidence=0.55,
            new_confidence=0.72,
            change_type="upgrade",
        )
        entry = WatchlistEntry(
            id=1,
            ticker="AAPL",
            webhook_url="https://example.com/hook",
        )

        fail_resp = httpx.Response(500, json={"error": "server error"})
        fail_resp._request = httpx.Request("POST", "https://example.com/hook")
        ok_resp = httpx.Response(200, json={"ok": True})
        ok_resp._request = httpx.Request("POST", "https://example.com/hook")

        with patch(
            "httpx.AsyncClient.post",
            new_callable=AsyncMock,
            side_effect=[fail_resp, ok_resp],
        ):
            result = await alert_engine.deliver_webhook(change, entry)
        assert result.success is True
        assert result.retries_used == 1

    @pytest.mark.asyncio
    async def test_deliver_webhook_hmac_signature(self, alert_engine):
        from integrations.alerts import SignalChange, WatchlistEntry

        alert_engine._webhook_secret = "test-secret-key"

        change = SignalChange(
            ticker="AAPL",
            old_signal="HOLD",
            new_signal="BUY",
            old_confidence=0.55,
            new_confidence=0.72,
            change_type="upgrade",
        )
        entry = WatchlistEntry(
            id=1,
            ticker="AAPL",
            webhook_url="https://example.com/hook",
        )

        captured_headers = {}
        captured_body = None

        async def mock_post(url, json=None, headers=None, timeout=None):
            nonlocal captured_headers, captured_body
            captured_headers = headers or {}
            captured_body = json
            resp = httpx.Response(200, json={"ok": True})
            resp._request = httpx.Request("POST", url)
            return resp

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
            await alert_engine.deliver_webhook(change, entry)

        assert "X-EquityIQ-Signature" in captured_headers
        # Verify HMAC
        expected_sig = hmac.new(
            b"test-secret-key",
            json.dumps(captured_body, sort_keys=True, default=str).encode(),
            hashlib.sha256,
        ).hexdigest()
        assert captured_headers["X-EquityIQ-Signature"] == f"sha256={expected_sig}"


# ---------------------------------------------------------------------------
# Alert History (FR-5)
# ---------------------------------------------------------------------------


class TestAlertHistory:
    @pytest.mark.asyncio
    async def test_record_alert_and_query(self, alert_engine):
        from integrations.alerts import DeliveryResult, SignalChange

        change = SignalChange(
            ticker="AAPL",
            old_signal="HOLD",
            new_signal="BUY",
            old_confidence=0.55,
            new_confidence=0.72,
            change_type="upgrade",
        )
        delivery = DeliveryResult(
            success=True,
            status_code=200,
            retries_used=0,
        )

        await alert_engine._record_alert(change, delivery, "https://example.com/hook")
        alerts = await alert_engine.get_recent_alerts(limit=10)
        assert len(alerts) == 1
        assert alerts[0].ticker == "AAPL"
        assert alerts[0].new_signal == "BUY"
        assert alerts[0].delivery_success is True

    @pytest.mark.asyncio
    async def test_get_alerts_by_ticker(self, alert_engine):
        from integrations.alerts import DeliveryResult, SignalChange

        for ticker in ["AAPL", "MSFT", "AAPL"]:
            change = SignalChange(
                ticker=ticker,
                old_signal="HOLD",
                new_signal="BUY",
                old_confidence=0.5,
                new_confidence=0.7,
                change_type="upgrade",
            )
            delivery = DeliveryResult(success=True, status_code=200, retries_used=0)
            await alert_engine._record_alert(change, delivery, "https://example.com")

        aapl_alerts = await alert_engine.get_alerts_by_ticker("AAPL")
        assert len(aapl_alerts) == 2

    @pytest.mark.asyncio
    async def test_prune_old_alerts(self, alert_engine):
        from integrations.alerts import DeliveryResult, SignalChange

        change = SignalChange(
            ticker="AAPL",
            old_signal="HOLD",
            new_signal="BUY",
            old_confidence=0.5,
            new_confidence=0.7,
            change_type="upgrade",
        )
        delivery = DeliveryResult(success=True, status_code=200, retries_used=0)
        await alert_engine._record_alert(change, delivery, "https://example.com")

        # Prune with 0 days retention = prune everything
        pruned = await alert_engine.prune_old_alerts(retention_days=0)
        assert pruned >= 1
        alerts = await alert_engine.get_recent_alerts(limit=10)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# Scheduler (FR-2)
# ---------------------------------------------------------------------------


class TestScheduler:
    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self, alert_engine):
        mock_conductor = AsyncMock()
        alert_engine.start_scheduler(mock_conductor, interval_minutes=15)
        assert alert_engine.scheduler_running is True

        await alert_engine.stop_scheduler()
        assert alert_engine.scheduler_running is False

    @pytest.mark.asyncio
    async def test_scheduler_clamps_interval(self, alert_engine):
        mock_conductor = AsyncMock()
        alert_engine.start_scheduler(mock_conductor, interval_minutes=5)
        # Should clamp to 15
        assert alert_engine._scheduler_interval >= 15
        await alert_engine.stop_scheduler()


# ---------------------------------------------------------------------------
# Full Flow (FR-2 + FR-3 + FR-4)
# ---------------------------------------------------------------------------


class TestCheckSignals:
    @pytest.mark.asyncio
    async def test_check_signals_full_flow(self, alert_engine):
        """check_signals re-analyzes watched tickers and detects changes."""
        # Add a watch
        await alert_engine.add_watch("AAPL", "https://example.com/hook")

        # Mock conductor to return a verdict
        mock_conductor = AsyncMock()
        mock_conductor.analyze.return_value = _make_verdict("AAPL", "BUY", 0.72)

        # Mock vault for previous verdict (None = first time)
        mock_vault = AsyncMock()
        mock_vault.get_latest_verdict_by_ticker = AsyncMock(return_value=None)

        # Mock webhook delivery
        mock_resp = httpx.Response(200, json={"ok": True})
        mock_resp._request = httpx.Request("POST", "https://example.com/hook")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            changes = await alert_engine.check_signals(mock_conductor, mock_vault)

        assert len(changes) >= 1
        assert changes[0].ticker == "AAPL"
        assert changes[0].change_type == "initial"


# ---------------------------------------------------------------------------
# API Endpoints (FR-6)
# ---------------------------------------------------------------------------


class TestAPIEndpoints:
    @pytest.mark.asyncio
    async def test_api_watchlist_crud(self):
        """Test watchlist CRUD via FastAPI test client."""

        from fastapi.testclient import TestClient

        from integrations.alerts import AlertEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_api.db")

            engine = AlertEngine(db_path=db_path)

            async def mock_lifespan(app):
                await engine.initialize()
                app.state.alert_engine = engine
                app.state.conductor = AsyncMock()
                app.state.vault = AsyncMock()
                yield
                await engine.close()

            from fastapi import FastAPI

            from api.webhooks import router as webhook_router

            app = FastAPI(lifespan=mock_lifespan)
            app.include_router(webhook_router)

            with TestClient(app) as client:
                # Add
                resp = client.post(
                    "/api/v1/alerts/watchlist",
                    json={"ticker": "AAPL", "webhook_url": "https://example.com/hook"},
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["ticker"] == "AAPL"
                entry_id = data["id"]

                # List
                resp = client.get("/api/v1/alerts/watchlist")
                assert resp.status_code == 200
                assert len(resp.json()) == 1

                # Delete
                resp = client.delete(f"/api/v1/alerts/watchlist/{entry_id}")
                assert resp.status_code == 200

                # Verify deleted
                resp = client.get("/api/v1/alerts/watchlist")
                assert resp.status_code == 200
                assert len(resp.json()) == 0

    @pytest.mark.asyncio
    async def test_api_check_now(self):
        """Test check-now endpoint."""
        from fastapi.testclient import TestClient

        from integrations.alerts import AlertEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_api.db")
            engine = AlertEngine(db_path=db_path)

            async def mock_lifespan(app):
                await engine.initialize()
                app.state.alert_engine = engine
                app.state.conductor = AsyncMock()
                app.state.vault = AsyncMock()
                yield
                await engine.close()

            from fastapi import FastAPI

            from api.webhooks import router as webhook_router

            app = FastAPI(lifespan=mock_lifespan)
            app.include_router(webhook_router)

            with TestClient(app) as client:
                resp = client.post("/api/v1/alerts/check-now")
                assert resp.status_code == 200
                assert "changes" in resp.json()

    @pytest.mark.asyncio
    async def test_api_alert_history(self):
        """Test alert history endpoint."""
        from fastapi.testclient import TestClient

        from integrations.alerts import AlertEngine

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_api.db")
            engine = AlertEngine(db_path=db_path)

            async def mock_lifespan(app):
                await engine.initialize()
                app.state.alert_engine = engine
                app.state.conductor = AsyncMock()
                app.state.vault = AsyncMock()
                yield
                await engine.close()

            from fastapi import FastAPI

            from api.webhooks import router as webhook_router

            app = FastAPI(lifespan=mock_lifespan)
            app.include_router(webhook_router)

            with TestClient(app) as client:
                resp = client.get("/api/v1/alerts/history")
                assert resp.status_code == 200
                assert isinstance(resp.json(), list)
