# Checklist S17.4 -- Webhook and Alert System

## Settings & Models
- [x] Add ALERT_CHECK_INTERVAL_MINUTES, ALERT_WEBHOOK_SECRET, ALERT_MAX_WATCHLIST_SIZE, ALERT_HISTORY_RETENTION_DAYS to config/settings.py
- [x] Define WatchlistEntry, SignalChange, DeliveryResult, AlertRecord Pydantic models in integrations/alerts.py

## Core Engine (integrations/alerts.py)
- [x] AlertEngine.__init__ with db_path (shared with InsightVault)
- [x] AlertEngine.initialize() -- create watchlist + alert_history tables
- [x] AlertEngine.add_watch(ticker, webhook_url, channel) -- insert/update watchlist
- [x] AlertEngine.remove_watch(entry_id) -- deactivate watchlist entry
- [x] AlertEngine.get_watchlist() -- return active entries
- [x] AlertEngine.check_signals(conductor) -- re-analyze all watched tickers, detect changes
- [x] AlertEngine._detect_signal_change(ticker, new_verdict, old_verdict) -- compare with previous verdict
- [x] AlertEngine.deliver_webhook(signal_change, watchlist_entry) -- POST with retry + HMAC
- [x] AlertEngine._record_alert(signal_change, delivery_result) -- persist to alert_history
- [x] AlertEngine.get_recent_alerts(limit) -- query alert_history
- [x] AlertEngine.get_alerts_by_ticker(ticker) -- query alert_history filtered
- [x] AlertEngine.get_failed_deliveries() -- query failed deliveries
- [x] AlertEngine.prune_old_alerts(retention_days) -- delete old records
- [x] AlertEngine.start_scheduler(conductor, interval_minutes) -- background asyncio.Task
- [x] AlertEngine.stop_scheduler() -- cancel background task
- [x] AlertEngine.close() -- cleanup DB connection

## API Endpoints (api/webhooks.py)
- [x] POST /api/v1/alerts/watchlist -- add ticker to watchlist
- [x] GET /api/v1/alerts/watchlist -- list watched tickers
- [x] DELETE /api/v1/alerts/watchlist/{entry_id} -- remove entry
- [x] GET /api/v1/alerts/history -- recent alert history
- [x] GET /api/v1/alerts/history/{ticker} -- alerts for ticker
- [x] POST /api/v1/alerts/check-now -- trigger immediate check
- [x] GET /api/v1/alerts/status -- scheduler status

## App Wiring (app.py)
- [x] Initialize AlertEngine in lifespan startup
- [x] Start scheduler in lifespan startup
- [x] Stop scheduler + close AlertEngine in lifespan shutdown
- [x] Include webhooks router in create_app()

## Tests (tests/test_alerts.py)
- [x] test_add_watch_creates_entry
- [x] test_add_watch_duplicate_updates
- [x] test_add_watch_max_limit
- [x] test_remove_watch
- [x] test_get_watchlist_active_only
- [x] test_detect_change_upgrade
- [x] test_detect_change_downgrade
- [x] test_detect_change_no_change
- [x] test_detect_change_initial (no previous verdict)
- [x] test_detect_change_confidence_shift
- [x] test_deliver_webhook_success
- [x] test_deliver_webhook_retry_on_failure
- [x] test_deliver_webhook_hmac_signature
- [x] test_record_alert_and_query
- [x] test_prune_old_alerts
- [x] test_scheduler_start_stop
- [x] test_check_signals_full_flow
- [x] test_api_watchlist_crud
- [x] test_api_check_now
- [x] test_api_alert_history

## Roadmap Update
- [x] Update roadmap.md status for S17.4 from pending -> done
