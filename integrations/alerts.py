"""Webhook alert system -- watchlist, signal change detection, and notification delivery."""

from __future__ import annotations

import asyncio
import hashlib
import hmac as hmac_module
import json
import logging
from datetime import datetime, timezone

import aiosqlite
import httpx
from pydantic import BaseModel, Field

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Signal ordering for upgrade/downgrade detection
SIGNAL_ORDER = {
    "STRONG_SELL": 0,
    "SELL": 1,
    "HOLD": 2,
    "BUY": 3,
    "STRONG_BUY": 4,
}

MIN_SCHEDULER_INTERVAL = 15  # minutes
MAX_WEBHOOK_RETRIES = 3
WEBHOOK_TIMEOUT = 10  # seconds
CONFIDENCE_SHIFT_THRESHOLD = 0.15

_CREATE_WATCHLIST_SQL = """
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'webhook',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_CREATE_ALERT_HISTORY_SQL = """
CREATE TABLE IF NOT EXISTS alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    old_signal TEXT,
    new_signal TEXT NOT NULL,
    old_confidence REAL,
    new_confidence REAL NOT NULL,
    change_type TEXT NOT NULL,
    webhook_url TEXT,
    delivery_success INTEGER,
    delivery_status_code INTEGER,
    retries_used INTEGER DEFAULT 0,
    detected_at TEXT NOT NULL,
    delivered_at TEXT
);
"""

_CREATE_WATCHLIST_INDEX = "CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON watchlist (ticker);"
_CREATE_HISTORY_INDEX = (
    "CREATE INDEX IF NOT EXISTS idx_alert_history_ticker ON alert_history (ticker);"
)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class WatchlistEntry(BaseModel):
    """A ticker on the user's watchlist."""

    id: int = 0
    ticker: str
    webhook_url: str
    channel: str = "webhook"
    active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SignalChange(BaseModel):
    """Detected signal change for a watched ticker."""

    ticker: str
    old_signal: str | None = None
    new_signal: str
    old_confidence: float | None = None
    new_confidence: float
    change_type: str  # "upgrade", "downgrade", "no_change", "initial", "confidence_shift"
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DeliveryResult(BaseModel):
    """Result of a webhook delivery attempt."""

    success: bool = False
    status_code: int | None = None
    response_snippet: str = ""
    retries_used: int = 0


class AlertRecord(BaseModel):
    """Persisted alert record for history."""

    id: int = 0
    ticker: str = ""
    old_signal: str | None = None
    new_signal: str = ""
    old_confidence: float | None = None
    new_confidence: float = 0.0
    change_type: str = ""
    webhook_url: str | None = None
    delivery_success: bool | None = None
    delivery_status_code: int | None = None
    retries_used: int = 0
    detected_at: str = ""
    delivered_at: str | None = None


# ---------------------------------------------------------------------------
# AlertEngine
# ---------------------------------------------------------------------------


class AlertEngine:
    """Core alert engine: watchlist management, signal detection, webhook delivery."""

    def __init__(self, db_path: str | None = None):
        settings = get_settings()
        self._db_path = db_path or settings.SQLITE_DB_PATH
        self._conn: aiosqlite.Connection | None = None
        self._max_watchlist_size = settings.ALERT_MAX_WATCHLIST_SIZE
        self._webhook_secret = settings.ALERT_WEBHOOK_SECRET
        self._retention_days = settings.ALERT_HISTORY_RETENTION_DAYS
        self._scheduler_task: asyncio.Task | None = None
        self._scheduler_interval: int = settings.ALERT_CHECK_INTERVAL_MINUTES
        self._last_check: str | None = None

    @property
    def scheduler_running(self) -> bool:
        return self._scheduler_task is not None and not self._scheduler_task.done()

    async def initialize(self) -> None:
        """Create DB tables if needed."""
        import os

        parent = os.path.dirname(self._db_path) or "."
        os.makedirs(parent, exist_ok=True)
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute(_CREATE_WATCHLIST_SQL)
        await self._conn.execute(_CREATE_ALERT_HISTORY_SQL)
        await self._conn.execute(_CREATE_WATCHLIST_INDEX)
        await self._conn.execute(_CREATE_HISTORY_INDEX)
        await self._conn.commit()
        logger.info("AlertEngine initialized (db=%s)", self._db_path)

    async def close(self) -> None:
        """Close DB connection."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        if self._conn:
            await self._conn.close()
            self._conn = None

    # ----- Watchlist Management (FR-1) -----

    async def add_watch(
        self, ticker: str, webhook_url: str, channel: str = "webhook"
    ) -> WatchlistEntry:
        """Add a ticker to the watchlist. Updates if duplicate ticker+url exists."""
        ticker = ticker.strip().upper()
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing entry (same ticker + webhook_url)
        cursor = await self._conn.execute(
            "SELECT id FROM watchlist WHERE ticker = ? AND webhook_url = ? AND active = 1",
            (ticker, webhook_url),
        )
        row = await cursor.fetchone()
        if row:
            # Update existing
            await self._conn.execute(
                "UPDATE watchlist SET channel = ?, updated_at = ? WHERE id = ?",
                (channel, now, row[0]),
            )
            await self._conn.commit()
            return WatchlistEntry(
                id=row[0],
                ticker=ticker,
                webhook_url=webhook_url,
                channel=channel,
                active=True,
                created_at=now,
                updated_at=now,
            )

        # Check watchlist size limit
        cursor = await self._conn.execute("SELECT COUNT(*) FROM watchlist WHERE active = 1")
        count_row = await cursor.fetchone()
        if count_row and count_row[0] >= self._max_watchlist_size:
            raise ValueError(f"watchlist limit reached ({self._max_watchlist_size})")

        # Insert new
        cursor = await self._conn.execute(
            "INSERT INTO watchlist (ticker, webhook_url, channel, active, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?)",
            (ticker, webhook_url, channel, now, now),
        )
        await self._conn.commit()
        return WatchlistEntry(
            id=cursor.lastrowid,
            ticker=ticker,
            webhook_url=webhook_url,
            channel=channel,
            active=True,
            created_at=now,
            updated_at=now,
        )

    async def remove_watch(self, entry_id: int) -> bool:
        """Deactivate a watchlist entry by ID."""
        cursor = await self._conn.execute(
            "UPDATE watchlist SET active = 0, updated_at = ? WHERE id = ? AND active = 1",
            (datetime.now(timezone.utc).isoformat(), entry_id),
        )
        await self._conn.commit()
        return cursor.rowcount > 0

    async def get_watchlist(self) -> list[WatchlistEntry]:
        """Return all active watchlist entries."""
        cursor = await self._conn.execute(
            "SELECT id, ticker, webhook_url, channel, active, created_at, updated_at "
            "FROM watchlist WHERE active = 1 ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            WatchlistEntry(
                id=r[0],
                ticker=r[1],
                webhook_url=r[2],
                channel=r[3],
                active=bool(r[4]),
                created_at=r[5],
                updated_at=r[6],
            )
            for r in rows
        ]

    # ----- Signal Change Detection (FR-3) -----

    def _detect_signal_change(self, ticker: str, new_verdict, old_verdict) -> SignalChange:
        """Compare new vs old verdict and classify the change."""
        new_signal = new_verdict.final_signal
        new_confidence = new_verdict.overall_confidence

        if old_verdict is None:
            return SignalChange(
                ticker=ticker,
                old_signal=None,
                new_signal=new_signal,
                old_confidence=None,
                new_confidence=new_confidence,
                change_type="initial",
            )

        old_signal = old_verdict.final_signal
        old_confidence = old_verdict.overall_confidence

        if new_signal == old_signal:
            # Check confidence shift
            if abs(new_confidence - old_confidence) >= CONFIDENCE_SHIFT_THRESHOLD:
                change_type = "confidence_shift"
            else:
                change_type = "no_change"
        elif SIGNAL_ORDER.get(new_signal, 2) > SIGNAL_ORDER.get(old_signal, 2):
            change_type = "upgrade"
        else:
            change_type = "downgrade"

        return SignalChange(
            ticker=ticker,
            old_signal=old_signal,
            new_signal=new_signal,
            old_confidence=old_confidence,
            new_confidence=new_confidence,
            change_type=change_type,
        )

    # ----- Webhook Delivery (FR-4) -----

    async def deliver_webhook(self, change: SignalChange, entry: WatchlistEntry) -> DeliveryResult:
        """POST signal change to webhook URL with retry and HMAC."""
        payload = {
            "ticker": change.ticker,
            "old_signal": change.old_signal,
            "new_signal": change.new_signal,
            "old_confidence": change.old_confidence,
            "new_confidence": change.new_confidence,
            "change_type": change.change_type,
            "detected_at": change.detected_at,
        }

        headers = {"Content-Type": "application/json"}
        if self._webhook_secret:
            body_bytes = json.dumps(payload, sort_keys=True, default=str).encode()
            sig = hmac_module.new(
                self._webhook_secret.encode(), body_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-EquityIQ-Signature"] = f"sha256={sig}"

        retries = 0
        last_status = None
        for attempt in range(MAX_WEBHOOK_RETRIES):
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        entry.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=WEBHOOK_TIMEOUT,
                    )
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    return DeliveryResult(
                        success=True,
                        status_code=resp.status_code,
                        response_snippet=resp.text[:200] if resp.text else "",
                        retries_used=retries,
                    )
                retries += 1
                if attempt < MAX_WEBHOOK_RETRIES - 1:
                    await asyncio.sleep(2**attempt)
            except Exception as exc:
                logger.warning(
                    "Webhook delivery attempt %d failed for %s: %s",
                    attempt + 1,
                    entry.webhook_url,
                    exc,
                )
                retries += 1
                if attempt < MAX_WEBHOOK_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

        return DeliveryResult(
            success=False,
            status_code=last_status,
            retries_used=retries,
        )

    # ----- Alert History (FR-5) -----

    async def _record_alert(
        self, change: SignalChange, delivery: DeliveryResult, webhook_url: str = ""
    ) -> None:
        """Persist alert to history table."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self._conn.execute(
                "INSERT INTO alert_history "
                "(ticker, old_signal, new_signal, old_confidence, new_confidence, "
                "change_type, webhook_url, delivery_success, delivery_status_code, "
                "retries_used, detected_at, delivered_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    change.ticker,
                    change.old_signal,
                    change.new_signal,
                    change.old_confidence,
                    change.new_confidence,
                    change.change_type,
                    webhook_url,
                    1 if delivery.success else 0,
                    delivery.status_code,
                    delivery.retries_used,
                    change.detected_at,
                    now if delivery.success else None,
                ),
            )
            await self._conn.commit()
        except Exception as exc:
            logger.error("Failed to record alert: %s", exc)

    async def get_recent_alerts(self, limit: int = 50) -> list[AlertRecord]:
        """Get recent alert history."""
        cursor = await self._conn.execute(
            "SELECT id, ticker, old_signal, new_signal, old_confidence, new_confidence, "
            "change_type, webhook_url, delivery_success, delivery_status_code, "
            "retries_used, detected_at, delivered_at "
            "FROM alert_history ORDER BY detected_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            AlertRecord(
                id=r[0],
                ticker=r[1],
                old_signal=r[2],
                new_signal=r[3],
                old_confidence=r[4],
                new_confidence=r[5],
                change_type=r[6],
                webhook_url=r[7],
                delivery_success=bool(r[8]) if r[8] is not None else None,
                delivery_status_code=r[9],
                retries_used=r[10] or 0,
                detected_at=r[11],
                delivered_at=r[12],
            )
            for r in rows
        ]

    async def get_alerts_by_ticker(self, ticker: str) -> list[AlertRecord]:
        """Get alerts for a specific ticker."""
        ticker = ticker.strip().upper()
        cursor = await self._conn.execute(
            "SELECT id, ticker, old_signal, new_signal, old_confidence, new_confidence, "
            "change_type, webhook_url, delivery_success, delivery_status_code, "
            "retries_used, detected_at, delivered_at "
            "FROM alert_history WHERE ticker = ? ORDER BY detected_at DESC",
            (ticker,),
        )
        rows = await cursor.fetchall()
        return [
            AlertRecord(
                id=r[0],
                ticker=r[1],
                old_signal=r[2],
                new_signal=r[3],
                old_confidence=r[4],
                new_confidence=r[5],
                change_type=r[6],
                webhook_url=r[7],
                delivery_success=bool(r[8]) if r[8] is not None else None,
                delivery_status_code=r[9],
                retries_used=r[10] or 0,
                detected_at=r[11],
                delivered_at=r[12],
            )
            for r in rows
        ]

    async def get_failed_deliveries(self) -> list[AlertRecord]:
        """Get alerts where delivery failed."""
        cursor = await self._conn.execute(
            "SELECT id, ticker, old_signal, new_signal, old_confidence, new_confidence, "
            "change_type, webhook_url, delivery_success, delivery_status_code, "
            "retries_used, detected_at, delivered_at "
            "FROM alert_history WHERE delivery_success = 0 ORDER BY detected_at DESC",
        )
        rows = await cursor.fetchall()
        return [
            AlertRecord(
                id=r[0],
                ticker=r[1],
                old_signal=r[2],
                new_signal=r[3],
                old_confidence=r[4],
                new_confidence=r[5],
                change_type=r[6],
                webhook_url=r[7],
                delivery_success=False,
                delivery_status_code=r[9],
                retries_used=r[10] or 0,
                detected_at=r[11],
                delivered_at=r[12],
            )
            for r in rows
        ]

    async def prune_old_alerts(self, retention_days: int | None = None) -> int:
        """Delete alert history older than retention_days."""
        days = retention_days if retention_days is not None else self._retention_days
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = await self._conn.execute(
            "DELETE FROM alert_history WHERE detected_at < ?", (cutoff,)
        )
        await self._conn.commit()
        return cursor.rowcount

    # ----- Check Signals (FR-2 + FR-3 + FR-4 combined) -----

    async def check_signals(self, conductor, vault) -> list[SignalChange]:
        """Re-analyze all watched tickers, detect changes, deliver webhooks."""
        watchlist = await self.get_watchlist()
        if not watchlist:
            return []

        changes: list[SignalChange] = []
        for entry in watchlist:
            try:
                # Re-analyze
                new_verdict = await conductor.analyze(entry.ticker)

                # Get previous verdict
                old_verdict = None
                try:
                    old_verdict = await vault.get_latest_verdict_by_ticker(entry.ticker)
                except Exception:
                    pass

                # Detect change
                change = self._detect_signal_change(entry.ticker, new_verdict, old_verdict)
                changes.append(change)

                # Deliver webhook if signal actually changed
                if change.change_type not in ("no_change",):
                    delivery = await self.deliver_webhook(change, entry)
                    await self._record_alert(change, delivery, entry.webhook_url)

                # Rate limit between tickers
                await asyncio.sleep(2)
            except Exception as exc:
                logger.error("Failed to check signal for %s: %s", entry.ticker, exc)

        self._last_check = datetime.now(timezone.utc).isoformat()
        return changes

    # ----- Scheduler (FR-2) -----

    def start_scheduler(self, conductor, interval_minutes: int | None = None) -> None:
        """Start background scheduler for periodic signal checks."""
        if self.scheduler_running:
            logger.warning("Scheduler already running, skipping")
            return

        interval = interval_minutes or self._scheduler_interval
        self._scheduler_interval = max(interval, MIN_SCHEDULER_INTERVAL)

        async def _loop():
            while True:
                try:
                    await asyncio.sleep(self._scheduler_interval * 60)
                    logger.info("Scheduler: running signal check")
                    # vault needs to be passed -- we'll get it from conductor if available
                    vault = getattr(conductor, "_vault", None) or getattr(conductor, "vault", None)
                    if vault:
                        await self.check_signals(conductor, vault)
                    else:
                        logger.warning("Scheduler: no vault available, skipping check")
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Scheduler error: %s", exc)

        self._scheduler_task = asyncio.create_task(_loop())
        logger.info("Alert scheduler started (interval=%d min)", self._scheduler_interval)

    async def stop_scheduler(self) -> None:
        """Stop the background scheduler."""
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        self._scheduler_task = None
        logger.info("Alert scheduler stopped")

    def get_status(self) -> dict:
        """Return scheduler status."""
        return {
            "scheduler_running": self.scheduler_running,
            "interval_minutes": self._scheduler_interval,
            "last_check": self._last_check,
            "webhook_secret_configured": bool(self._webhook_secret),
        }
