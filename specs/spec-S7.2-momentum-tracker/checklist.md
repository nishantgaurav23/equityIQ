# Checklist S7.2 -- Momentum Tracker Agent

## Implementation Tasks

- [x] Create `agents/momentum_tracker.py`
- [x] Implement `get_technical_analysis(ticker)` tool function
  - [x] Fetch price history from PolygonConnector (250 days)
  - [x] Compute RSI via calc_rsi()
  - [x] Compute MACD via calc_macd()
  - [x] Compute SMA 50 and SMA 200 via calc_sma()
  - [x] Determine above_sma_50 and above_sma_200 flags
  - [x] Classify volume_trend (increasing/decreasing/stable)
  - [x] Compute price_momentum_score (composite, clamped [-1,1])
  - [x] Handle empty/error cases with None fallbacks
- [x] Implement `MomentumTrackerAgent(BaseAnalystAgent)`
  - [x] Init with momentum_tracker persona, MomentumReport, tools
- [x] Create module-level `agent` instance
- [x] Add `agents/__init__.py` if not exists

## Test Tasks

- [x] Create `tests/test_momentum_tracker.py`
- [x] Tool function tests (tests 1-15)
  - [x] test_get_technical_analysis_success
  - [x] test_get_technical_analysis_empty_prices
  - [x] test_get_technical_analysis_polygon_error
  - [x] test_rsi_calculation
  - [x] test_macd_calculation
  - [x] test_sma_crossover_above
  - [x] test_sma_crossover_below
  - [x] test_sma_crossover_mixed
  - [x] test_volume_trend_increasing
  - [x] test_volume_trend_decreasing
  - [x] test_volume_trend_stable
  - [x] test_momentum_score_bullish
  - [x] test_momentum_score_bearish
  - [x] test_momentum_score_clamped
  - [x] test_get_technical_analysis_insufficient_data
- [x] Agent tests (tests 16-23)
  - [x] test_agent_class_is_base_analyst
  - [x] test_agent_name
  - [x] test_agent_output_schema
  - [x] test_agent_tools_include_technical_analysis
  - [x] test_agent_card
  - [x] test_module_level_agent_instance
  - [x] test_analyze_success
  - [x] test_analyze_failure_fallback

## Verification

- [x] All tests pass: `python -m pytest tests/test_momentum_tracker.py -v`
- [x] Lint passes: `ruff check agents/momentum_tracker.py`
- [x] All spec outcomes met
