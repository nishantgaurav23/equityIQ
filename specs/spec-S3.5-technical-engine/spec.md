# Spec S3.5 -- Technical Engine

## Overview
Pure Python technical indicator calculator for the MomentumTracker agent. Provides `calc_rsi()`, `calc_macd()`, `calc_sma()`, and `calc_volatility()` functions using numpy only -- no external API calls, no caching needed. These functions consume price history arrays (from Polygon connector) and return numeric indicator values used to populate `MomentumReport`.

## Dependencies
None (`--`). This module has no spec dependencies -- it is a pure computation library.

## Target Location
`tools/technical_engine.py`

---

## Functional Requirements

### FR-1: calc_rsi(prices, period=14)
- **What**: Calculate Relative Strength Index from a list of closing prices
- **Inputs**: `prices: list[float]` (closing prices, oldest first), `period: int` (default 14)
- **Outputs**: `float` -- RSI value clamped to [0.0, 100.0]
- **Algorithm**: Standard Wilder's RSI -- average gain / average loss over the period using exponential moving average (EMA) smoothing
- **Edge cases**:
  - Fewer prices than `period + 1` -> return 50.0 (neutral)
  - All gains (no losses) -> return 100.0
  - All losses (no gains) -> return 0.0
  - Empty list -> return 50.0

### FR-2: calc_macd(prices, fast=12, slow=26, signal=9)
- **What**: Calculate MACD line, signal line, and histogram
- **Inputs**: `prices: list[float]` (closing prices, oldest first), `fast: int` (default 12), `slow: int` (default 26), `signal: int` (default 9)
- **Outputs**: `dict` with keys `macd_line: float`, `signal_line: float`, `histogram: float`
- **Algorithm**: MACD line = EMA(fast) - EMA(slow); Signal line = EMA(signal) of MACD line; Histogram = MACD - Signal
- **Edge cases**:
  - Fewer prices than `slow + signal` -> return `{"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0}`
  - Empty list -> return zeros dict

### FR-3: calc_sma(prices, period)
- **What**: Calculate Simple Moving Average over the given period
- **Inputs**: `prices: list[float]` (closing prices, oldest first), `period: int`
- **Outputs**: `float` -- the SMA value (average of last `period` prices)
- **Edge cases**:
  - Fewer prices than `period` -> return average of all available prices
  - Empty list -> return 0.0
  - Single price -> return that price

### FR-4: calc_volatility(prices, period=252)
- **What**: Calculate annualized volatility from daily closing prices
- **Inputs**: `prices: list[float]` (closing prices, oldest first), `period: int` (trading days for annualization, default 252)
- **Outputs**: `float` -- annualized volatility as a decimal (e.g., 0.25 = 25%)
- **Algorithm**: Standard deviation of daily log returns, multiplied by sqrt(period)
- **Edge cases**:
  - Fewer than 2 prices -> return 0.0
  - Empty list -> return 0.0
  - Constant prices (zero variance) -> return 0.0

### FR-5: Helper -- EMA calculation
- **What**: Internal helper to compute Exponential Moving Average
- **Inputs**: `values: list[float]`, `period: int`
- **Outputs**: `list[float]` -- EMA series
- **Note**: Used internally by calc_rsi and calc_macd. May be private (`_calc_ema`).

---

## Tangible Outcomes

- [ ] **Outcome 1**: `calc_rsi([...50 prices...])` returns a float in [0, 100]
- [ ] **Outcome 2**: `calc_rsi` with all-up prices returns ~100.0; all-down returns ~0.0
- [ ] **Outcome 3**: `calc_macd([...50 prices...])` returns dict with `macd_line`, `signal_line`, `histogram` keys
- [ ] **Outcome 4**: `calc_sma([10, 20, 30], 3)` returns 20.0
- [ ] **Outcome 5**: `calc_volatility` with constant prices returns 0.0
- [ ] **Outcome 6**: `calc_volatility` with known data returns expected annualized vol
- [ ] **Outcome 7**: All functions handle edge cases (empty list, insufficient data) without raising exceptions
- [ ] **Outcome 8**: Module has zero external API dependencies -- only numpy + stdlib

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_calc_rsi_basic**: RSI of a known price series matches expected value
2. **test_calc_rsi_all_up**: Monotonically increasing prices -> RSI near 100
3. **test_calc_rsi_all_down**: Monotonically decreasing prices -> RSI near 0
4. **test_calc_rsi_insufficient_data**: Fewer than period+1 prices -> returns 50.0
5. **test_calc_rsi_empty**: Empty list -> returns 50.0
6. **test_calc_macd_basic**: MACD of known series returns expected dict
7. **test_calc_macd_insufficient_data**: Short list -> returns zeros dict
8. **test_calc_macd_empty**: Empty list -> returns zeros dict
9. **test_calc_macd_keys**: Result has exactly macd_line, signal_line, histogram keys
10. **test_calc_sma_basic**: SMA of [10, 20, 30] period=3 -> 20.0
11. **test_calc_sma_partial**: Fewer prices than period -> average of available
12. **test_calc_sma_empty**: Empty list -> 0.0
13. **test_calc_volatility_basic**: Known series returns expected annualized vol
14. **test_calc_volatility_constant**: Constant prices -> 0.0
15. **test_calc_volatility_insufficient**: Fewer than 2 prices -> 0.0
16. **test_calc_volatility_empty**: Empty list -> 0.0
17. **test_no_external_api_deps**: Module imports contain no httpx/aiohttp/requests

### Mocking Strategy
- No mocking needed -- this is a pure computation module with no external dependencies

### Coverage Expectation
- All 4 public functions tested with normal, edge, and boundary cases
- 100% branch coverage on edge case guards

---

## References
- roadmap.md -- S3.5 row in Phase 3 table
- design.md -- technical_engine in tools layer
- config/data_contracts.py -- MomentumReport (rsi_14, macd_signal, above_sma_50, above_sma_200, price_momentum_score)
- S7.2 MomentumTracker agent will be the primary consumer
