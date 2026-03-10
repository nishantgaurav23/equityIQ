# Spec S17.3 -- Portfolio Sync from Brokers

## Overview
Auto-import holdings from connected Zerodha and Alpaca broker accounts. Run `analyze_portfolio()` on the imported tickers to generate EquityIQ verdicts. Present a side-by-side comparison of current holdings vs EquityIQ recommendations. Support periodic refresh on a configurable interval so the portfolio stays current without manual action.

## Dependencies
- **S17.1** -- Zerodha broker integration (`integrations/zerodha.py`)
- **S17.2** -- Alpaca broker integration (`integrations/alpaca.py`)
- **S8.3** -- Portfolio analysis (`agents/market_conductor.py` -- `analyze_portfolio()`)

## Target Location
- `integrations/portfolio_sync.py`

---

## Functional Requirements

### FR-1: Unified Portfolio Import
- **What**: Fetch holdings from one or both connected brokers (Zerodha, Alpaca) and merge into a single unified holding list with broker source tags.
- **Inputs**: Broker credentials/tokens (Zerodha access_token, Alpaca API key pair). Optional broker filter (`zerodha`, `alpaca`, or `all`).
- **Outputs**: `UnifiedPortfolio` model containing a list of `UnifiedHolding` items, each with: ticker (EquityIQ format), quantity, avg_price, current_price, unrealized_pnl, broker_source (`zerodha`/`alpaca`).
- **Edge cases**: One broker disconnected or errored -- still return holdings from the other. Both brokers fail -- return empty portfolio with error flags. Duplicate tickers across brokers are kept separate (different broker_source).

### FR-2: Run Analysis on Imported Tickers
- **What**: Extract unique EquityIQ tickers from the unified portfolio and run `analyze_portfolio()` via the MarketConductor.
- **Inputs**: `UnifiedPortfolio` (from FR-1).
- **Outputs**: `PortfolioInsight` containing verdicts for all imported tickers.
- **Edge cases**: Empty portfolio (no tickers) -- return None/empty insight. More than 10 unique tickers -- batch in groups of 10. Analysis failure for some tickers -- partial results with reduced confidence.

### FR-3: Side-by-Side Comparison
- **What**: Generate a `SyncReport` that pairs each holding with its EquityIQ verdict, showing current position vs recommendation.
- **Inputs**: `UnifiedPortfolio` + `PortfolioInsight`.
- **Outputs**: `SyncReport` model containing a list of `HoldingComparison` items: ticker, broker_source, quantity, avg_price, current_price, unrealized_pnl, equityiq_signal, equityiq_confidence, action_hint (e.g., "HOLD aligns", "Consider SELL", "Consider adding").
- **Edge cases**: Ticker analyzed but no verdict (agent failure) -- action_hint = "Analysis unavailable". Holdings with no valid EquityIQ ticker mapping -- skip analysis, flag as "Unmapped".

### FR-4: Periodic Refresh via Background Scheduler
- **What**: Optionally schedule automatic portfolio sync at a configurable interval (default: 60 minutes). Uses `asyncio` task scheduling (no external dependency like Celery).
- **Inputs**: Refresh interval in minutes (configurable via settings), broker credentials.
- **Outputs**: Updated `SyncReport` stored in an in-memory cache (TTLCache) keyed by user/session.
- **Edge cases**: Refresh interval < 5 minutes -- clamp to 5 (avoid API rate limits). Scheduler already running -- skip duplicate. Graceful shutdown -- cancel background task on app shutdown.

### FR-5: API Endpoint for Portfolio Sync
- **What**: Expose `POST /api/portfolio/sync` endpoint that triggers a sync and returns the `SyncReport`. Expose `GET /api/portfolio/sync/status` to check last sync time and scheduler state.
- **Inputs**: JSON body with broker tokens/keys and optional `brokers` filter.
- **Outputs**: `SyncReport` JSON response.
- **Edge cases**: No broker credentials provided -- 400 error. Sync already in progress -- return 202 with "sync in progress" status.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `integrations/portfolio_sync.py` exists with `PortfolioSyncer` class exposing `sync()`, `get_comparison()`, and `start_scheduler()`/`stop_scheduler()` methods
- [ ] **Outcome 2**: Pydantic models `UnifiedHolding`, `UnifiedPortfolio`, `HoldingComparison`, `SyncReport` defined and validated
- [ ] **Outcome 3**: Zerodha holdings + Alpaca positions merged into unified format with correct EquityIQ ticker mapping
- [ ] **Outcome 4**: `analyze_portfolio()` called on imported tickers and verdicts matched back to holdings
- [ ] **Outcome 5**: Side-by-side comparison generates correct `action_hint` based on signal vs current position
- [ ] **Outcome 6**: Background scheduler starts/stops cleanly and refreshes at configured interval
- [ ] **Outcome 7**: API endpoints wired into FastAPI app and return correct responses
- [ ] **Outcome 8**: All external calls (Zerodha, Alpaca, MarketConductor) wrapped in try/except -- never crashes

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_unified_holding_model**: Validate `UnifiedHolding` and `UnifiedPortfolio` Pydantic models
2. **test_import_zerodha_only**: Mock Zerodha client, verify holdings imported with `broker_source="zerodha"`
3. **test_import_alpaca_only**: Mock Alpaca client, verify positions imported with `broker_source="alpaca"`
4. **test_import_both_brokers**: Mock both, verify merged portfolio contains holdings from both
5. **test_import_broker_failure_graceful**: One broker raises exception, other still returns holdings
6. **test_import_both_fail**: Both brokers fail, returns empty portfolio with error flags
7. **test_run_analysis_on_tickers**: Mock `analyze_portfolio()`, verify called with correct unique tickers
8. **test_run_analysis_empty_portfolio**: Empty portfolio returns None
9. **test_run_analysis_batching**: >10 tickers split into batches of 10
10. **test_comparison_report**: Verify `HoldingComparison` correctly pairs holdings with verdicts
11. **test_comparison_action_hints**: BUY signal on held stock -> "HOLD aligns" or "Consider adding"; SELL signal -> "Consider SELL"
12. **test_comparison_unmapped_ticker**: Holding with no EquityIQ ticker -> flagged as "Unmapped"
13. **test_scheduler_start_stop**: Scheduler starts background task, stop cancels it
14. **test_scheduler_clamp_interval**: Interval < 5 min clamped to 5
15. **test_full_sync_flow**: End-to-end: import -> analyze -> compare, returns `SyncReport`

### Mocking Strategy
- `ZerodhaClient.get_portfolio_summary()` -- mock return `ZerodhaPortfolio`
- `AlpacaClient.get_portfolio_summary()` -- mock return `AlpacaPortfolio`
- `MarketConductor.analyze_portfolio()` -- mock return `PortfolioInsight`
- All via `pytest-mock` (`mocker.patch` / `AsyncMock`)

### Coverage Expectation
- All public methods on `PortfolioSyncer` have tests
- Edge cases: broker failures, empty portfolios, unmapped tickers, batching, scheduler lifecycle

---

## References
- `roadmap.md` -- S17.3 spec definition
- `design.md` -- architecture overview
- `integrations/zerodha.py` -- `ZerodhaClient`, `ZerodhaPortfolio`, `ZerodhaHolding`
- `integrations/alpaca.py` -- `AlpacaClient`, `AlpacaPortfolio`, `AlpacaPosition`
- `agents/market_conductor.py` -- `MarketConductor.analyze_portfolio()`
- `config/data_contracts.py` -- `PortfolioInsight`, `FinalVerdict`
