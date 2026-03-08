# S7.4 -- EconomyWatcher Agent

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S7.4 |
| Phase | 7 -- Specialist Agents |
| Depends On | S6.1 (agent base), S3.2 (FRED connector) |
| Location | `agents/economy_watcher.py` |
| Test | `tests/test_economy_watcher.py` |
| Status | spec-written |

## Purpose

Implement the EconomyWatcher specialist agent -- a macroeconomic analysis agent that fetches macro indicators from the FRED API via `FredConnector`, classifies the current macro regime, and returns an `EconomyReport` with a BUY/HOLD/SELL signal. Runs on Port 8004.

## Requirements

### R1: Agent Class -- `EconomyWatcher`

Create an `EconomyWatcher` class that extends `BaseAnalystAgent` from `agents/base_agent.py`.

- **agent_name**: `"economy_watcher"`
- **output_schema**: `EconomyReport`
- **tools**: Wrap `FredConnector` methods as ADK-compatible tool functions
- **model**: Default `"gemini-3-flash-preview"`

### R2: Tool Functions

Define standalone async tool functions that the ADK agent can invoke:

#### `get_macro_indicators_tool() -> dict`
- Calls `FredConnector.get_macro_indicators()`
- Returns the dict with keys: gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate, macro_regime
- Returns `{}` on error (never raises)

Note: Unlike other agents, this tool takes no `ticker` parameter since macro indicators are market-wide, not stock-specific.

### R3: Analyze Method

The `analyze(ticker)` method is inherited from `BaseAnalystAgent`. It:
1. Sends the ticker to the ADK agent with the EconomyWatcher persona
2. The LLM uses `get_macro_indicators_tool` to fetch macro data
3. The LLM interprets how macro conditions affect the specific ticker/sector
4. The LLM returns a JSON response matching `EconomyReport`
5. `BaseAnalystAgent.analyze()` validates the response via `EconomyReport.model_validate_json()`
6. On failure, returns a fallback HOLD/0.0 report

### R4: Convenience Factory

Provide a module-level `create_economy_watcher()` factory function:
```python
def create_economy_watcher() -> EconomyWatcher:
    return EconomyWatcher()
```

### R5: Module-Level Instance

Provide a default instance for easy import:
```python
economy_watcher = create_economy_watcher()
```

### R6: Error Handling

- All tool functions wrap external calls in try/except
- `FredConnector` errors return `{}` (already handled in connector)
- Agent-level errors caught by `BaseAnalystAgent.analyze()` fallback
- No exception propagates to the caller

## Signal Logic (from persona)

- **BUY**: Expansion or recovery regime -- favorable for most equities
- **SELL**: Contraction or stagflation regime -- headwinds for equities
- **HOLD**: Transitional period, mixed macro signals

## EconomyReport Fields

| Field | Type | Source |
|-------|------|--------|
| ticker | str | Input |
| agent_name | str | `"economy_watcher"` |
| signal | BUY/HOLD/SELL | LLM decision |
| confidence | float [0,1] | LLM decision |
| reasoning | str | LLM explanation |
| gdp_growth | float \| None | FRED GDP series |
| inflation_rate | float \| None | FRED CPI series |
| fed_funds_rate | float \| None | FRED FEDFUNDS series |
| unemployment_rate | float \| None | FRED UNRATE series |
| macro_regime | expansion/contraction/stagflation/recovery \| None | Classified from indicators |

## Test Plan

### T1: Instantiation
- `EconomyWatcher` creates successfully
- `agent_name` is `"economy_watcher"`
- `output_schema` is `EconomyReport`
- Tool functions are registered

### T2: Tool Functions
- `get_macro_indicators_tool()` calls `FredConnector.get_macro_indicators`
- Returns `{}` on connector error

### T3: Analyze (mocked LLM)
- Mock the ADK `Runner.run_async` to return a valid `EconomyReport` JSON
- Verify the returned report has correct ticker, agent_name, signal, confidence
- Verify macro fields (gdp_growth, macro_regime, etc.) are populated

### T4: Analyze Fallback
- Mock the ADK runner to raise an exception
- Verify fallback report: signal=HOLD, confidence=0.0

### T5: Agent Card
- `get_agent_card()` returns dict with correct name, capabilities, output_schema

### T6: Factory Function
- `create_economy_watcher()` returns an `EconomyWatcher` instance
- Module-level `economy_watcher` is an `EconomyWatcher` instance

## File Structure

```
agents/economy_watcher.py    <- Implementation
tests/test_economy_watcher.py <- Tests (all external services mocked)
```

## Acceptance Criteria

1. `EconomyWatcher` extends `BaseAnalystAgent` correctly
2. Tool function wraps `FredConnector.get_macro_indicators()` with error handling
3. `analyze("AAPL")` returns a valid `EconomyReport` (with mocked LLM)
4. Fallback returns HOLD/0.0 on any error
5. All tests pass: `pytest tests/test_economy_watcher.py -v`
6. Ruff clean: `ruff check agents/economy_watcher.py`
7. Agent card generation works correctly
