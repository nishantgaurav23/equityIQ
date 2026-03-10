# Spec S8.3 -- Multi-Stock Portfolio Analysis

## Overview
Adds `analyze_portfolio()` to `MarketConductor` in `agents/market_conductor.py`. This method runs `analyze()` for each ticker in a list, aggregates the individual `FinalVerdict` results into a `PortfolioInsight`, calculates a `diversification_score`, determines an overall `portfolio_signal`, and selects the `top_pick` (highest-confidence BUY/STRONG_BUY ticker).

## Dependencies
- **S8.2** -- MarketConductor orchestrator (provides `analyze()`)
- **S2.2** -- Data contracts (provides `PortfolioInsight`, `FinalVerdict`)

## Target Location
`agents/market_conductor.py`

---

## Functional Requirements

### FR-1: analyze_portfolio() method
- **What**: `MarketConductor.analyze_portfolio(tickers: list[str]) -> PortfolioInsight` runs `analyze()` for each ticker concurrently using `asyncio.gather()`, collects all `FinalVerdict` results, and returns a `PortfolioInsight`.
- **Inputs**: `tickers` -- list of 1-10 uppercase stock ticker strings.
- **Outputs**: `PortfolioInsight` with all fields populated.
- **Edge cases**:
  - Empty ticker list -> return PortfolioInsight with empty verdicts, HOLD signal, 0.0 diversification, no top_pick.
  - Single ticker -> diversification_score = 0.0 (no diversification benefit).
  - All analyses fail -> HOLD signal, 0.0 confidence, no top_pick.

### FR-2: Ticker validation and normalization
- **What**: Each ticker is stripped and uppercased before analysis. Duplicate tickers are deduplicated (keep first occurrence order).
- **Inputs**: Raw ticker strings (may have whitespace, mixed case, duplicates).
- **Outputs**: Cleaned, deduplicated list passed to analyze().
- **Edge cases**: All tickers are duplicates of one -> treated as single ticker.

### FR-3: Concurrent execution with error isolation
- **What**: All ticker analyses run concurrently via `asyncio.gather(..., return_exceptions=True)`. A failure for one ticker does not block others. Failed tickers are excluded from the final PortfolioInsight (with a warning logged).
- **Inputs**: N tickers.
- **Outputs**: Only successful FinalVerdicts included in `verdicts`.
- **Edge cases**: Partial failures -- only successful verdicts contribute to aggregation.

### FR-4: Portfolio signal aggregation
- **What**: Compute an overall `portfolio_signal` from the individual verdicts using a weighted-average approach:
  - Map each signal to a numeric score: STRONG_BUY=2, BUY=1, HOLD=0, SELL=-1, STRONG_SELL=-2.
  - Weight each score by the verdict's `overall_confidence`.
  - Compute weighted average score and map back: >= 1.5 -> STRONG_BUY, >= 0.5 -> BUY, > -0.5 -> HOLD, > -1.5 -> SELL, else -> STRONG_SELL.
  - STRONG_BUY/STRONG_SELL requires the highest individual confidence to be >= 0.75 (consistent with FinalVerdict rules).
- **Inputs**: List of FinalVerdicts.
- **Outputs**: Single portfolio_signal string.

### FR-5: Diversification score calculation
- **What**: Calculate `diversification_score` (0.0 to 1.0) based on signal diversity among verdicts:
  - Count the number of unique signals across verdicts.
  - Score = (unique_signals - 1) / (total_verdicts - 1), clamped to [0.0, 1.0].
  - Single ticker or empty -> 0.0.
  - All same signal -> 0.0. All different signals -> approaches 1.0.
- **Inputs**: List of FinalVerdicts.
- **Outputs**: Float in [0.0, 1.0].

### FR-6: Top pick selection
- **What**: Select `top_pick` as the ticker with the highest `overall_confidence` among verdicts with signal BUY or STRONG_BUY. If no BUY/STRONG_BUY verdicts exist, top_pick is `None`.
- **Inputs**: List of FinalVerdicts.
- **Outputs**: Ticker string or None.

### FR-7: Ticker limit enforcement
- **What**: Maximum 10 tickers per portfolio analysis. If more than 10 are provided, raise a `ValueError` with a descriptive message.
- **Inputs**: Ticker list.
- **Outputs**: ValueError if len > 10.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `MarketConductor().analyze_portfolio(["AAPL", "GOOGL", "MSFT"])` returns a `PortfolioInsight` with 3 verdicts (mocked agents).
- [ ] **Outcome 2**: Empty ticker list returns PortfolioInsight with HOLD, 0.0 diversification, no top_pick.
- [ ] **Outcome 3**: Duplicate tickers are deduplicated -- `["AAPL", "aapl", " AAPL"]` results in 1 verdict.
- [ ] **Outcome 4**: If one ticker's analysis fails, remaining tickers still return verdicts.
- [ ] **Outcome 5**: `portfolio_signal` correctly aggregates individual signals.
- [ ] **Outcome 6**: `diversification_score` is 0.0 for single ticker, > 0 for mixed signals.
- [ ] **Outcome 7**: `top_pick` is the highest-confidence BUY/STRONG_BUY ticker, or None if no buys.
- [ ] **Outcome 8**: More than 10 tickers raises ValueError.

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_analyze_portfolio_basic**: 3 tickers, all succeed, returns PortfolioInsight with 3 verdicts.
2. **test_analyze_portfolio_empty_tickers**: Empty list -> HOLD, 0.0 diversification, no top_pick.
3. **test_analyze_portfolio_single_ticker**: 1 ticker -> diversification_score = 0.0.
4. **test_analyze_portfolio_deduplication**: Duplicate tickers deduplicated.
5. **test_analyze_portfolio_ticker_normalization**: Mixed case/whitespace normalized.
6. **test_analyze_portfolio_partial_failure**: One ticker fails, others succeed.
7. **test_analyze_portfolio_all_fail**: All tickers fail -> HOLD, 0.0 confidence.
8. **test_portfolio_signal_aggregation_buy_majority**: Mostly BUY -> portfolio BUY.
9. **test_portfolio_signal_aggregation_sell_majority**: Mostly SELL -> portfolio SELL.
10. **test_portfolio_signal_aggregation_mixed**: Mixed signals -> HOLD.
11. **test_diversification_score_all_same**: All same signal -> 0.0.
12. **test_diversification_score_all_different**: All different signals -> > 0.
13. **test_top_pick_selection**: Highest-confidence BUY selected.
14. **test_top_pick_no_buys**: No BUY signals -> top_pick is None.
15. **test_ticker_limit_exceeded**: 11 tickers -> ValueError.
16. **test_analyze_portfolio_stores_verdicts**: Vault store called for each successful verdict.

### Mocking Strategy
- Mock `MarketConductor.analyze()` to return predetermined `FinalVerdict` objects (avoid invoking actual agents).
- Mock `InsightVault.store_verdict()` if vault is provided.
- Use `pytest-asyncio` for all async tests.

### Coverage Expectation
- All public methods (`analyze_portfolio`) and helper functions covered.
- Edge cases (empty, single, duplicates, failures, limits) all tested.

---

## References
- roadmap.md (S8.3 row)
- design.md (orchestration architecture)
- config/data_contracts.py (PortfolioInsight, FinalVerdict schemas)
- agents/market_conductor.py (MarketConductor.analyze())
