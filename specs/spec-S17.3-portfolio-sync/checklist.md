# Checklist -- Spec S17.3: Portfolio Sync from Brokers

## Phase 1: Setup & Dependencies
- [x] Verify S17.1 (Zerodha integration) is implemented and tests pass
- [x] Verify S17.2 (Alpaca integration) is implemented and tests pass
- [x] Verify S8.3 (portfolio analyzer) is implemented and tests pass
- [x] Create `integrations/portfolio_sync.py`
- [x] Add any new imports/dependencies to pyproject.toml if needed (none needed)

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_portfolio_sync.py`
- [x] Write failing tests for FR-1 (unified import from brokers)
- [x] Write failing tests for FR-2 (run analysis on imported tickers)
- [x] Write failing tests for FR-3 (side-by-side comparison)
- [x] Write failing tests for FR-4 (periodic refresh scheduler)
- [x] Write failing tests for FR-5 (full sync flow)
- [x] Run tests -- expect failures (Red) ✓ 26 failed

## Phase 3: Implementation
- [x] Define Pydantic models: `UnifiedHolding`, `UnifiedPortfolio`, `HoldingComparison`, `SyncReport`
- [x] Implement `PortfolioSyncer.__init__()` -- accept broker clients + conductor reference
- [x] Implement `PortfolioSyncer.import_holdings()` -- FR-1: fetch + merge from both brokers
- [x] Implement `PortfolioSyncer.run_analysis()` -- FR-2: call analyze_portfolio() with batching
- [x] Implement `PortfolioSyncer.get_comparison()` -- FR-3: pair holdings with verdicts, generate action_hints
- [x] Implement `PortfolioSyncer.sync()` -- FR-1+2+3 combined: import -> analyze -> compare
- [x] Implement `PortfolioSyncer.start_scheduler()` / `stop_scheduler()` -- FR-4: asyncio background task
- [x] Run tests -- expect pass (Green) ✓ 26 passed
- [x] Refactor -- ruff clean

## Phase 4: Integration
- [x] Ruff check and format pass
- [x] All 26 tests pass

## Phase 5: Verification
- [x] All tangible outcomes checked (8 outcomes)
- [x] No hardcoded secrets
- [x] All external calls wrapped in try/except
- [x] Logging includes relevant context (broker, ticker)
- [x] Roadmap updated to `done`
