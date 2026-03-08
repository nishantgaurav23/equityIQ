# S7.1 -- ValuationScout Agent

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S7.1 |
| Phase | 7 -- Specialist Agents |
| Depends On | S6.1 (agent base), S3.1 (polygon connector) |
| Location | `agents/valuation_scout.py` |
| Test | `tests/test_valuation_scout.py` |
| Status | spec-written |

## Purpose

Implement the ValuationScout specialist agent -- a fundamental analysis agent that fetches financial data from Polygon.io via `PolygonConnector`, computes valuation metrics, and returns a `ValuationReport` with a BUY/HOLD/SELL signal.

## Requirements

### R1: Agent Class -- `ValuationScout`

Create a `ValuationScout` class that extends `BaseAnalystAgent` from `agents/base_agent.py`.

- **agent_name**: `"valuation_scout"`
- **output_schema**: `ValuationReport`
- **tools**: Wrap `PolygonConnector` methods as ADK-compatible tool functions
- **model**: Default `"gemini-3-flash-preview"`

### R2: Tool Functions

Define standalone async tool functions that the ADK agent can invoke:

#### `get_fundamentals_tool(ticker: str) -> dict`
- Calls `PolygonConnector.get_fundamentals(ticker)`
- Returns the raw dict from Polygon (pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield)
- Returns `{}` on error (never raises)

#### `get_price_history_tool(ticker: str) -> dict`
- Calls `PolygonConnector.get_price_history(ticker, days=365)`
- Used for intrinsic value gap estimation (needs price data)
- Returns `{}` on error (never raises)

### R3: Analyze Method

The `analyze(ticker)` method is inherited from `BaseAnalystAgent`. It:
1. Sends the ticker to the ADK agent with the ValuationScout persona
2. The LLM uses the tool functions to fetch data
3. The LLM returns a JSON response matching `ValuationReport`
4. `BaseAnalystAgent.analyze()` validates the response via `ValuationReport.model_validate_json()`
5. On failure, returns a fallback HOLD/0.0 report

### R4: Convenience Factory

Provide a module-level `create_valuation_scout()` factory function:
```python
def create_valuation_scout() -> ValuationScout:
    return ValuationScout()
```

### R5: Module-Level Instance

Provide a default instance for easy import:
```python
valuation_scout = create_valuation_scout()
```

### R6: Error Handling

- All tool functions wrap external calls in try/except
- `PolygonConnector` errors return `{}` (already handled)
- Agent-level errors caught by `BaseAnalystAgent.analyze()` fallback
- No exception propagates to the caller

## Signal Logic (from persona)

- **BUY**: Stock is undervalued (intrinsic_value_gap > 0), strong fundamentals
- **SELL**: Stock is overvalued (intrinsic_value_gap < 0), deteriorating fundamentals
- **HOLD**: Fairly valued, mixed signals across metrics

## ValuationReport Fields

| Field | Type | Source |
|-------|------|--------|
| ticker | str | Input |
| agent_name | str | `"valuation_scout"` |
| signal | BUY/HOLD/SELL | LLM decision |
| confidence | float [0,1] | LLM decision |
| reasoning | str | LLM explanation |
| pe_ratio | float \| None | Polygon fundamentals |
| pb_ratio | float \| None | Polygon fundamentals |
| revenue_growth | float \| None | Polygon fundamentals |
| debt_to_equity | float \| None | Polygon fundamentals |
| fcf_yield | float \| None | Polygon fundamentals |
| intrinsic_value_gap | float \| None | LLM estimate |

## Test Plan

### T1: Instantiation
- `ValuationScout` creates successfully
- `agent_name` is `"valuation_scout"`
- `output_schema` is `ValuationReport`
- Tool functions are registered

### T2: Tool Functions
- `get_fundamentals_tool("AAPL")` calls `PolygonConnector.get_fundamentals`
- `get_price_history_tool("AAPL")` calls `PolygonConnector.get_price_history`
- Both return `{}` on connector error

### T3: Analyze (mocked LLM)
- Mock the ADK `Runner.run_async` to return a valid `ValuationReport` JSON
- Verify the returned report has correct ticker, agent_name, signal, confidence
- Verify valuation fields (pe_ratio, etc.) are populated

### T4: Analyze Fallback
- Mock the ADK runner to raise an exception
- Verify fallback report: signal=HOLD, confidence=0.0

### T5: Agent Card
- `get_agent_card()` returns dict with correct name, capabilities, output_schema

### T6: Factory Function
- `create_valuation_scout()` returns a `ValuationScout` instance
- Module-level `valuation_scout` is a `ValuationScout` instance

## File Structure

```
agents/valuation_scout.py   <- Implementation
tests/test_valuation_scout.py <- Tests (all external services mocked)
```

## Acceptance Criteria

1. `ValuationScout` extends `BaseAnalystAgent` correctly
2. Tool functions wrap `PolygonConnector` calls with error handling
3. `analyze("AAPL")` returns a valid `ValuationReport` (with mocked LLM)
4. Fallback returns HOLD/0.0 on any error
5. All tests pass: `pytest tests/test_valuation_scout.py -v`
6. Ruff clean: `ruff check agents/valuation_scout.py`
7. Agent card generation works correctly
