# Spec S7.2 -- Momentum Tracker Agent

## Overview

Specialist agent that performs technical analysis on a given stock ticker. Uses `polygon_connector` to fetch price history and `technical_engine` to compute RSI, MACD, SMA crossovers, and volatility. Returns a `MomentumReport` with directional signal (BUY/HOLD/SELL), confidence, and all technical indicator fields populated.

## Location

`agents/momentum_tracker.py`

## Dependencies

| Spec | What it provides |
|------|-----------------|
| S6.1 | `agents/base_agent.py` -- BaseAnalystAgent, create_agent() |
| S3.1 | `tools/polygon_connector.py` -- PolygonConnector.get_price_history() |
| S3.5 | `tools/technical_engine.py` -- calc_rsi(), calc_macd(), calc_sma(), calc_volatility() |
| S2.1 | `config/data_contracts.py` -- MomentumReport schema |
| S2.3 | `config/analyst_personas.py` -- PERSONAS["momentum_tracker"] |

## Public API

### Module-level

```python
# Pre-built agent instance ready for use
agent: MomentumTrackerAgent

# Tool functions exposed to the ADK agent
async def get_technical_analysis(ticker: str) -> dict:
    """
    Fetch price history from Polygon, compute all technical indicators,
    and return a structured dict with RSI, MACD, SMA crossovers, volume
    trend, and momentum score.
    """
```

### `MomentumTrackerAgent(BaseAnalystAgent)`

Extends `BaseAnalystAgent` with momentum-specific tool binding and analysis logic.

```python
class MomentumTrackerAgent(BaseAnalystAgent):
    """Technical analysis agent using price momentum indicators."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        """Initialize with momentum_tracker persona and MomentumReport schema."""
        super().__init__(
            agent_name="momentum_tracker",
            output_schema=MomentumReport,
            tools=[get_technical_analysis],
            model=model,
        )
```

## Implementation Details

### `get_technical_analysis(ticker)` Tool Function

This is the ADK tool function that the LLM agent calls to gather data. It:

1. Creates a `PolygonConnector` instance
2. Calls `get_price_history(ticker, days=250)` -- 250 days for SMA 200 coverage
3. If price history is empty, returns a fallback dict with all None values
4. Extracts `prices` and `volumes` lists from the response
5. Computes indicators using `technical_engine`:
   - `rsi_14 = calc_rsi(prices, period=14)`
   - `macd = calc_macd(prices)` -> extracts `macd_line`, `signal_line`, `histogram`
   - `sma_50 = calc_sma(prices, period=50)`
   - `sma_200 = calc_sma(prices, period=200)`
   - `volatility = calc_volatility(prices)`
6. Determines SMA crossover flags:
   - `above_sma_50`: `prices[-1] > sma_50` (if prices available)
   - `above_sma_200`: `prices[-1] > sma_200` (if prices available)
7. Determines `volume_trend`:
   - Compare average volume of last 10 days vs last 30 days
   - If recent avg > 1.2x longer avg: `"increasing"`
   - If recent avg < 0.8x longer avg: `"decreasing"`
   - Otherwise: `"stable"`
8. Computes `price_momentum_score` -- composite in [-1.0, 1.0]:
   - RSI component: `(rsi_14 - 50) / 50` (maps 0-100 -> -1 to 1)
   - MACD component: `1.0 if histogram > 0 else -1.0 if histogram < 0 else 0.0`
   - SMA component: `+0.5 if above_sma_50 else -0.5` + `+0.5 if above_sma_200 else -0.5`
   - Average all three, clamp to [-1.0, 1.0]
9. Returns dict with all computed values
10. On any error, returns fallback dict with all None values and logs warning

### Signal Logic (determined by LLM persona)

The LLM uses the persona's signal logic instructions and the tool output to decide:
- **BUY**: RSI oversold bounce, bullish MACD crossover, price above SMAs, increasing volume
- **SELL**: RSI overbought reversal, bearish MACD crossover, price below SMAs
- **HOLD**: Mixed or neutral indicators

### Error Handling

- `get_technical_analysis` wraps all calls in try/except, returns fallback dict on error
- `BaseAnalystAgent.analyze()` provides outer error handling (HOLD/0.0 fallback)
- Polygon API failures result in degraded (None-valued) report, not crash

## Tangible Outcomes

1. `agents/momentum_tracker.py` exists with `MomentumTrackerAgent` class and `get_technical_analysis()` tool
2. Module-level `agent` instance is created for import convenience
3. All tests pass: `python -m pytest tests/test_momentum_tracker.py -v`
4. `ruff check agents/momentum_tracker.py` passes with no errors
5. `get_technical_analysis()` fetches price data and computes all 6 indicator fields
6. Handles empty/missing price data gracefully (None fallbacks)
7. Volume trend classification works correctly (increasing/decreasing/stable)
8. Price momentum score is computed and clamped to [-1.0, 1.0]
9. Agent inherits BaseAnalystAgent behavior: analyze(), get_agent_card(), error fallback

## Test Plan

### Unit Tests (`tests/test_momentum_tracker.py`)

All Polygon API calls and ADK/LLM calls must be mocked.

#### Tool Function Tests

1. **test_get_technical_analysis_success** -- mock Polygon with valid price data, verify all fields returned (rsi_14, macd_signal, above_sma_50, above_sma_200, volume_trend, price_momentum_score)
2. **test_get_technical_analysis_empty_prices** -- mock Polygon returning `{}`, verify all fields are None
3. **test_get_technical_analysis_polygon_error** -- mock Polygon raising exception, verify fallback dict returned
4. **test_rsi_calculation** -- verify RSI is computed from price data via calc_rsi
5. **test_macd_calculation** -- verify MACD histogram value is extracted
6. **test_sma_crossover_above** -- price above both SMAs -> both True
7. **test_sma_crossover_below** -- price below both SMAs -> both False
8. **test_sma_crossover_mixed** -- price above 50 but below 200 -> mixed
9. **test_volume_trend_increasing** -- recent volume > 1.2x avg -> "increasing"
10. **test_volume_trend_decreasing** -- recent volume < 0.8x avg -> "decreasing"
11. **test_volume_trend_stable** -- neutral volume -> "stable"
12. **test_momentum_score_bullish** -- bullish indicators -> positive score
13. **test_momentum_score_bearish** -- bearish indicators -> negative score
14. **test_momentum_score_clamped** -- score stays in [-1.0, 1.0]
15. **test_get_technical_analysis_insufficient_data** -- fewer than 15 prices -> defaults used (RSI=50)

#### Agent Tests

16. **test_agent_class_is_base_analyst** -- MomentumTrackerAgent inherits BaseAnalystAgent
17. **test_agent_name** -- agent.name == "momentum_tracker"
18. **test_agent_output_schema** -- output_schema is MomentumReport
19. **test_agent_tools_include_technical_analysis** -- tools list includes get_technical_analysis
20. **test_agent_card** -- get_agent_card() returns valid dict with correct name and capabilities
21. **test_module_level_agent_instance** -- `momentum_tracker.agent` is a MomentumTrackerAgent
22. **test_analyze_success** -- mock LLM to return valid MomentumReport JSON, verify parsed result
23. **test_analyze_failure_fallback** -- mock LLM failure, verify HOLD/0.0 fallback
