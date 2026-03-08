# Spec S4.2 -- Risk Calculator

## Overview
Pure-math portfolio risk module providing the core calculations used by the RiskGuardian agent. Implements beta, Sharpe ratio, Value-at-Risk (95%), maximum drawdown, and position sizing. All functions are stateless, using numpy/pandas on price series data. Position size is hard-capped at 0.10 (10% max per stock).

## Dependencies
- **S2.1** (Analyst Report Schemas) -- RiskGuardianReport defines the output fields this module computes

## Target Location
- `models/risk_calculator.py`

---

## Functional Requirements

### FR-1: calc_beta(stock_returns, market_returns)
- **What**: Calculate the beta coefficient of a stock relative to a market benchmark
- **Inputs**: `stock_returns: list[float] | np.ndarray`, `market_returns: list[float] | np.ndarray` -- daily return series
- **Outputs**: `float` -- beta value (covariance / variance of market)
- **Edge cases**:
  - Empty or single-element arrays -> return 1.0 (market-neutral default)
  - Zero variance in market returns -> return 1.0
  - Mismatched lengths -> raise ValueError

### FR-2: calc_sharpe(returns, risk_free_rate=0.05)
- **What**: Calculate the annualized Sharpe ratio
- **Inputs**: `returns: list[float] | np.ndarray` -- daily return series, `risk_free_rate: float` -- annualized risk-free rate (default 0.05)
- **Outputs**: `float` -- annualized Sharpe ratio
- **Formula**: `(mean_daily_return - daily_rf) / std_daily_return * sqrt(252)`
- **Edge cases**:
  - Empty or single-element arrays -> return 0.0
  - Zero standard deviation -> return 0.0

### FR-3: calc_var_95(returns)
- **What**: Calculate the historical Value-at-Risk at 95% confidence level
- **Inputs**: `returns: list[float] | np.ndarray` -- daily return series
- **Outputs**: `float` -- the 5th percentile of the return distribution (a negative number representing worst expected daily loss)
- **Edge cases**:
  - Empty array -> return 0.0
  - Single-element array -> return that element

### FR-4: calc_max_drawdown(prices)
- **What**: Calculate the maximum peak-to-trough drawdown from a price series
- **Inputs**: `prices: list[float] | np.ndarray` -- daily closing prices (not returns)
- **Outputs**: `float` -- maximum drawdown as a negative fraction (e.g., -0.25 = 25% drawdown)
- **Edge cases**:
  - Empty or single-element array -> return 0.0
  - Monotonically increasing prices -> return 0.0

### FR-5: calc_position_size(volatility, max_portfolio_risk=0.02, max_position=0.10)
- **What**: Calculate suggested position size based on volatility targeting
- **Inputs**: `volatility: float` -- annualized volatility, `max_portfolio_risk: float` -- max acceptable risk contribution (default 0.02), `max_position: float` -- hard cap (default 0.10)
- **Outputs**: `float` -- suggested allocation fraction, capped at `max_position`
- **Formula**: `min(max_portfolio_risk / volatility, max_position)` if volatility > 0
- **Edge cases**:
  - Zero or negative volatility -> return max_position (low vol = safe to max out)
  - Result always clamped to [0.0, max_position]

### FR-6: calc_annualized_volatility(returns)
- **What**: Calculate annualized volatility from daily returns
- **Inputs**: `returns: list[float] | np.ndarray` -- daily return series
- **Outputs**: `float` -- annualized volatility (std * sqrt(252))
- **Edge cases**:
  - Empty or single-element array -> return 0.0

---

## Tangible Outcomes

- [ ] **Outcome 1**: `from models.risk_calculator import calc_beta, calc_sharpe, calc_var_95, calc_max_drawdown, calc_position_size, calc_annualized_volatility` works
- [ ] **Outcome 2**: calc_beta with known inputs produces correct covariance/variance result
- [ ] **Outcome 3**: calc_sharpe returns annualized ratio matching hand-calculated value
- [ ] **Outcome 4**: calc_var_95 returns the 5th percentile of the distribution
- [ ] **Outcome 5**: calc_max_drawdown correctly identifies the worst peak-to-trough decline
- [ ] **Outcome 6**: calc_position_size never exceeds 0.10 (hard cap)
- [ ] **Outcome 7**: All edge cases (empty arrays, zero variance, mismatched lengths) handled gracefully
- [ ] **Outcome 8**: All functions are pure (no external API calls, no side effects)

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_calc_beta_known_values**: Known stock/market returns -> verify correct beta
2. **test_calc_beta_identical_returns**: Stock == market -> beta should be 1.0
3. **test_calc_beta_empty_returns**: Empty arrays -> returns 1.0
4. **test_calc_beta_mismatched_lengths**: Different length arrays -> raises ValueError
5. **test_calc_beta_zero_market_variance**: Constant market returns -> returns 1.0
6. **test_calc_sharpe_positive**: Positive-return series -> positive Sharpe
7. **test_calc_sharpe_empty**: Empty returns -> 0.0
8. **test_calc_sharpe_zero_std**: Constant returns -> 0.0
9. **test_calc_var_95_known**: Known distribution -> verify 5th percentile
10. **test_calc_var_95_empty**: Empty -> 0.0
11. **test_calc_max_drawdown_known**: Price series with known drawdown -> verify
12. **test_calc_max_drawdown_monotonic_up**: Always increasing -> 0.0
13. **test_calc_max_drawdown_empty**: Empty -> 0.0
14. **test_calc_position_size_normal**: Normal volatility -> correct size
15. **test_calc_position_size_capped**: Low volatility -> capped at 0.10
16. **test_calc_position_size_zero_vol**: Zero volatility -> max_position
17. **test_calc_annualized_volatility_known**: Known std -> verify * sqrt(252)
18. **test_calc_annualized_volatility_empty**: Empty -> 0.0

### Mocking Strategy
- No mocking needed -- all functions are pure math (numpy/pandas only)

### Coverage Expectation
- All 6 public functions tested with normal + edge cases
- 100% branch coverage for edge-case guards

---

## References
- roadmap.md -- Phase 4, S4.2
- design.md -- RiskGuardian agent architecture
- config/data_contracts.py -- RiskGuardianReport schema
