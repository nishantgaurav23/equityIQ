# Spec S17.4 -- Webhook and Alert System

## Overview
Watchlist-based alert system that monitors user-selected tickers, detects signal changes from previous verdicts, and delivers notifications via webhooks (HTTP POST to user-configured URLs). Optional: email via SendGrid or Telegram bot integration. Background scheduler re-analyzes watched tickers on a configurable interval.

## Dependencies
- **S10.1** -- Pipeline wiring (`app.py` -- full analysis pipeline)
- **S5.1** -- InsightVault (`memory/insight_vault.py` -- verdict storage)

## Target Location
- `integrations/alerts.py` -- core alert engine (watchlist, scheduler, signal change detection)
- `api/webhooks.py` -- API endpoints for managing watchlists and webhook configuration

---

## Functional Requirements

### FR-1: Watchlist Management
- **What**: Users can add/remove tickers to a persistent watchlist. Each watchlist entry stores the ticker, a webhook URL for delivery, and optional notification preferences.
- **Inputs**: Ticker symbol, webhook URL, optional notification channel (`webhook`, `telegram`, `email`). User/session identifier.
- **Outputs**: `WatchlistEntry` model with id, ticker, webhook_url, channel, active status, created_at.
- **Storage**: SQLite table `watchlist` (async via aiosqlite), same DB as InsightVault.
- **Edge cases**: Duplicate ticker+webhook combo -- update existing entry. Invalid ticker format -- reject with 400. Empty webhook URL when channel is `webhook` -- reject. Max 50 entries per user to prevent abuse.

### FR-2: Background Scheduler for Re-Analysis
- **What**: Background `asyncio.Task` that periodically re-analyzes all watched tickers. Uses MarketConductor to run full analysis pipeline.
- **Inputs**: Configurable interval via `ALERT_CHECK_INTERVAL_MINUTES` setting (default: 60, min: 15 to respect API limits).
- **Outputs**: Fresh `FinalVerdict` for each watched ticker, stored in InsightVault.
- **Edge cases**: Scheduler already running -- skip duplicate. Interval < 15 min -- clamp to 15. Analysis failure for a ticker -- log error, skip that ticker, continue with others. Graceful shutdown -- cancel task on app shutdown. Rate limiting -- batch tickers with 2s delay between analyses.

### FR-3: Signal Change Detection
- **What**: Compare the latest verdict for each watched ticker against the previous verdict. Detect meaningful signal changes (e.g., BUY -> SELL, HOLD -> STRONG_BUY).
- **Inputs**: Current `FinalVerdict`, previous `FinalVerdict` (from InsightVault history).
- **Outputs**: `SignalChange` model with ticker, old_signal, new_signal, old_confidence, new_confidence, change_type (`upgrade`, `downgrade`, `no_change`), detected_at.
- **Logic**: Signal ordering: STRONG_SELL < SELL < HOLD < BUY < STRONG_BUY. Change = new != old. Upgrade = new > old. Downgrade = new < old.
- **Edge cases**: No previous verdict (first analysis) -- treat as `new_signal` with change_type `initial`. Same signal but confidence changed by >= 0.15 -- emit as `confidence_shift` type.

### FR-4: Webhook Delivery
- **What**: When a signal change is detected, deliver a notification payload to the configured webhook URL via HTTP POST.
- **Inputs**: `SignalChange`, `WatchlistEntry` (contains webhook_url).
- **Outputs**: `DeliveryResult` model with success bool, status_code, response snippet, retries_used.
- **Payload**: JSON body with: ticker, old_signal, new_signal, confidence, change_type, analyzed_at, equityiq_url.
- **Retry**: Up to 3 attempts with exponential backoff (1s, 2s, 4s). Timeout: 10s per attempt.
- **Edge cases**: Webhook URL unreachable -- log failure, mark delivery as failed, continue. Non-2xx response -- retry. Invalid URL format -- skip delivery, log warning. HMAC signature header (`X-EquityIQ-Signature`) for payload verification using a configurable secret.

### FR-5: Alert History
- **What**: Store all signal changes and delivery attempts in SQLite for auditing and user review.
- **Inputs**: `SignalChange` + `DeliveryResult`.
- **Outputs**: `AlertRecord` model stored in `alert_history` table.
- **Queries**: `get_recent_alerts(limit)`, `get_alerts_by_ticker(ticker)`, `get_failed_deliveries()`.
- **Edge cases**: DB write failure -- log error, don't crash. History grows large -- auto-prune records older than 90 days.

### FR-6: API Endpoints
- **What**: REST endpoints for watchlist CRUD, alert history, and scheduler control.
- **Endpoints**:
  - `POST /api/v1/alerts/watchlist` -- Add ticker to watchlist
  - `GET /api/v1/alerts/watchlist` -- List all watched tickers
  - `DELETE /api/v1/alerts/watchlist/{entry_id}` -- Remove from watchlist
  - `GET /api/v1/alerts/history` -- Get recent alert history
  - `GET /api/v1/alerts/history/{ticker}` -- Get alerts for a specific ticker
  - `POST /api/v1/alerts/check-now` -- Trigger immediate re-analysis of all watched tickers
  - `GET /api/v1/alerts/status` -- Scheduler status (running/stopped, last check time, next check time)
- **Edge cases**: Empty watchlist on check-now -- return 200 with empty results. Scheduler not started -- status shows `stopped`.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `integrations/alerts.py` exists with `AlertEngine` class exposing `add_watch()`, `remove_watch()`, `get_watchlist()`, `check_signals()`, `deliver_webhook()`, `start_scheduler()`, `stop_scheduler()`
- [ ] **Outcome 2**: Pydantic models `WatchlistEntry`, `SignalChange`, `DeliveryResult`, `AlertRecord` defined and validated
- [ ] **Outcome 3**: SQLite tables `watchlist` and `alert_history` created on init (same DB as InsightVault)
- [ ] **Outcome 4**: Signal change detection correctly identifies upgrades, downgrades, initial signals, and confidence shifts
- [ ] **Outcome 5**: Webhook delivery with retry logic (3 attempts, exponential backoff) and HMAC signature
- [ ] **Outcome 6**: Background scheduler starts/stops cleanly, respects interval clamping, handles failures gracefully
- [ ] **Outcome 7**: `api/webhooks.py` with all 7 endpoints wired into FastAPI app
- [ ] **Outcome 8**: Alert history persisted and queryable, auto-prune after 90 days
- [ ] **Outcome 9**: All external calls (webhook POST, analysis pipeline) wrapped in try/except -- never crashes
- [ ] **Outcome 10**: `tests/test_alerts.py` with >= 15 tests covering all FRs

---

## Settings (config/settings.py additions)

```python
# Alert system
ALERT_CHECK_INTERVAL_MINUTES: int = 60
ALERT_WEBHOOK_SECRET: str = ""  # HMAC signing key
ALERT_MAX_WATCHLIST_SIZE: int = 50
ALERT_HISTORY_RETENTION_DAYS: int = 90
```

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'webhook',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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
```
