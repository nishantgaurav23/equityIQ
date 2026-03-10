# Checklist -- Spec S8.3: Multi-Stock Portfolio Analysis

## Phase 1: Setup & Dependencies
- [x] Verify S8.2 (MarketConductor) is implemented and tests pass
- [x] Verify S2.2 (data contracts -- PortfolioInsight) is implemented
- [x] Locate target file: agents/market_conductor.py

## Phase 2: Tests First (TDD)
- [x] Write test file: tests/test_market_conductor.py (add portfolio tests)
- [x] Write failing tests for FR-1 (analyze_portfolio basic)
- [x] Write failing tests for FR-2 (ticker validation/dedup)
- [x] Write failing tests for FR-3 (concurrent execution/error isolation)
- [x] Write failing tests for FR-4 (portfolio signal aggregation)
- [x] Write failing tests for FR-5 (diversification score)
- [x] Write failing tests for FR-6 (top pick selection)
- [x] Write failing tests for FR-7 (ticker limit)
- [x] Run tests -- expect failures (Red) -- 17 failed, 15 passed

## Phase 3: Implementation
- [x] Implement helper: _compute_portfolio_signal(verdicts) -> str
- [x] Implement helper: _compute_diversification_score(verdicts) -> float
- [x] Implement helper: _select_top_pick(verdicts) -> str | None
- [x] Implement analyze_portfolio(tickers) on MarketConductor
- [x] Run tests -- expect pass (Green) -- 32 passed
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify analyze_portfolio is accessible from MarketConductor instance
- [x] Update A2A adapter if needed (expose portfolio endpoint) -- N/A, S9.2 will handle API exposure
- [x] Run ruff linting -- All checks passed
- [x] Run full test suite -- 632 passed

## Phase 5: Verification
- [x] All 8 tangible outcomes checked
- [x] No hardcoded secrets
- [x] Logging includes ticker list for portfolio analysis
- [x] Update roadmap.md status: spec-written -> done
