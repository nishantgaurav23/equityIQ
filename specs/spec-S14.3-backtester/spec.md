# Spec S14.3 -- Historical Backtesting

## Overview
Historical backtesting engine that runs the analysis pipeline on historical data, compares predicted signals against actual price movements, and tracks accuracy metrics. Uses stored FinalVerdicts from InsightVault (via HistoryRetriever) and fetches actual price data to evaluate whether BUY/SELL/HOLD signals were correct over configurable time windows (30/60/90 days). Produces accuracy reports per ticker, per agent, and overall.

## Dependencies
- S14.2 (Benchmark Cases) -- benchmark infrastructure, BenchmarkCase model patterns
- S5.2 (History Retriever) -- access to past FinalVerdicts for backtesting

## Target Location
- `evaluation/backtester.py` -- backtester engine
- `tests/test_backtester.py` -- test suite

---

## Functional Requirements

### FR-1: BacktestConfig Model
- **What**: Pydantic model for configuring a backtest run
- **Inputs**: `ticker` (str), `windows` (list of int days, default [30, 60, 90]), `min_confidence` (float, default 0.0 -- filter low-confidence verdicts), `start_date` (optional datetime), `end_date` (optional datetime)
- **Outputs**: Validated config model
- **Edge cases**: Windows must be positive integers. min_confidence clamped to [0, 1].

### FR-2: BacktestResult Model
- **What**: Pydantic model for individual backtest outcome
- **Inputs**: `ticker`, `session_id`, `predicted_signal`, `predicted_confidence`, `price_at_prediction`, `price_after` (dict of window_days -> price), `actual_returns` (dict of window_days -> pct return), `outcomes` (dict of window_days -> "correct"/"incorrect"/"pending"), `verdict_date` (datetime)
- **Outputs**: Validated result model
- **Edge cases**: If price data unavailable for a window, outcome is "pending". actual_returns stored as decimal (0.05 = 5%).

### FR-3: BacktestSummary Model
- **What**: Aggregated metrics from a backtest run
- **Inputs**: `ticker`, `total_verdicts`, `evaluated_verdicts` (those with price data), `accuracy_by_window` (dict of window_days -> hit_rate float), `average_confidence`, `signal_distribution` (dict of signal -> count), `results` (list of BacktestResult)
- **Outputs**: Summary with pass rates per window
- **Edge cases**: If no evaluated verdicts, accuracy is None (not 0).

### FR-4: Backtester Class -- evaluate_verdict()
- **What**: Given a FinalVerdict and a price lookup function, evaluate whether the signal was correct for each time window
- **Inputs**: `verdict` (FinalVerdict), `price_lookup` (async callable: (ticker, date) -> float | None), `windows` (list of int days)
- **Outputs**: `BacktestResult`
- **Logic**:
  - BUY is correct if price went up (return > 0) within the window
  - SELL is correct if price went down (return < 0) within the window
  - HOLD is correct if absolute return < 5% within the window
  - STRONG_BUY / STRONG_SELL follow BUY / SELL rules respectively
  - If price_lookup returns None for a window, outcome is "pending"
- **Edge cases**: Zero return -> HOLD is correct, BUY/SELL are incorrect

### FR-5: Backtester Class -- run_backtest()
- **What**: Run a full backtest for a ticker using stored verdicts
- **Inputs**: `config` (BacktestConfig), `history_retriever` (HistoryRetriever), `price_lookup` (async callable)
- **Outputs**: `BacktestSummary`
- **Logic**:
  1. Fetch past verdicts via `history_retriever.get_ticker_history(ticker)`
  2. Filter by min_confidence and date range if provided
  3. For each verdict, call `evaluate_verdict()`
  4. Aggregate results into BacktestSummary
- **Edge cases**: No verdicts found -> return summary with total_verdicts=0. Price lookup failure -> try/except, mark as pending.

### FR-6: Backtester Class -- run_multi_ticker()
- **What**: Run backtests across multiple tickers
- **Inputs**: `tickers` (list of str), `history_retriever`, `price_lookup`, `windows`
- **Outputs**: dict of ticker -> BacktestSummary
- **Edge cases**: Empty ticker list -> return empty dict. Individual ticker failure -> log and continue.

### FR-7: Signal Correctness Logic
- **What**: Pure function `is_signal_correct(signal, actual_return)` encapsulating the correctness rules
- **Inputs**: `signal` (str: BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL), `actual_return` (float, decimal pct)
- **Outputs**: bool
- **Rules**:
  - BUY / STRONG_BUY: correct if actual_return > 0
  - SELL / STRONG_SELL: correct if actual_return < 0
  - HOLD: correct if abs(actual_return) < 0.05
- **Edge cases**: Unknown signal -> return False

---

## Tangible Outcomes

- [ ] **Outcome 1**: `evaluation/backtester.py` exists with `Backtester`, `BacktestConfig`, `BacktestResult`, `BacktestSummary` classes
- [ ] **Outcome 2**: `is_signal_correct()` function correctly maps all 5 signal types to price movements
- [ ] **Outcome 3**: `evaluate_verdict()` produces BacktestResult with outcomes per window
- [ ] **Outcome 4**: `run_backtest()` fetches historical verdicts, evaluates each, returns BacktestSummary with accuracy_by_window
- [ ] **Outcome 5**: `run_multi_ticker()` runs backtests across multiple tickers concurrently
- [ ] **Outcome 6**: All external calls (price lookup, history retrieval) are wrapped in try/except -- never crashes
- [ ] **Outcome 7**: Test file `tests/test_backtester.py` covers all FRs with at least 15 tests

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_backtest_config_defaults**: BacktestConfig with just ticker has correct defaults
2. **test_backtest_config_windows_positive**: Windows must be positive integers
3. **test_backtest_config_min_confidence_clamped**: min_confidence clamped to [0, 1]
4. **test_backtest_result_model_valid**: BacktestResult accepts valid data
5. **test_backtest_summary_model_valid**: BacktestSummary accepts valid data
6. **test_backtest_summary_no_evaluated**: accuracy_by_window is empty dict when no evaluated verdicts
7. **test_is_signal_correct_buy_up**: BUY + positive return -> True
8. **test_is_signal_correct_buy_down**: BUY + negative return -> False
9. **test_is_signal_correct_sell_down**: SELL + negative return -> True
10. **test_is_signal_correct_sell_up**: SELL + positive return -> False
11. **test_is_signal_correct_hold_small**: HOLD + small return (<5%) -> True
12. **test_is_signal_correct_hold_large**: HOLD + large return (>5%) -> False
13. **test_is_signal_correct_strong_buy**: STRONG_BUY follows BUY rules
14. **test_is_signal_correct_strong_sell**: STRONG_SELL follows SELL rules
15. **test_is_signal_correct_unknown**: Unknown signal -> False
16. **test_evaluate_verdict_all_windows**: Evaluates verdict across 30/60/90 day windows
17. **test_evaluate_verdict_missing_price**: Missing price -> outcome "pending"
18. **test_run_backtest_basic**: Run backtest with mock verdicts and prices
19. **test_run_backtest_confidence_filter**: min_confidence filters low-confidence verdicts
20. **test_run_backtest_date_filter**: start_date/end_date filters verdicts
21. **test_run_backtest_no_verdicts**: Empty history -> summary with total_verdicts=0
22. **test_run_backtest_price_lookup_failure**: Price error -> graceful handling, pending outcome
23. **test_run_multi_ticker**: Multiple tickers produce per-ticker summaries
24. **test_run_multi_ticker_empty**: Empty list -> empty dict
25. **test_run_multi_ticker_partial_failure**: One ticker fails -> others still succeed

### Mocking Strategy
- `HistoryRetriever.get_ticker_history()` -- mock to return deterministic FinalVerdicts
- `price_lookup` -- mock async callable returning known prices or None
- No external API calls needed (all data is mocked)

### Coverage Expectation
- All public functions and classes have tests
- Edge cases: zero returns, missing prices, empty histories, date boundaries
- Signal correctness rules exhaustively tested for all 5 signal types

---

## References
- roadmap.md -- S14.3 spec definition
- evaluation/quality_assessor.py -- QualityAssessor (S14.1)
- evaluation/benchmarks/ -- BenchmarkCase patterns (S14.2)
- memory/history_retriever.py -- HistoryRetriever (S5.2)
- config/data_contracts.py -- FinalVerdict, PredictionOutcome
- models/signal_fusion.py -- SignalSynthesizer signal types
