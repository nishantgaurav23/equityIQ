# S7.6 -- RiskGuardian Agent

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S7.6 |
| Phase | 7 -- Specialist Agents |
| Depends On | S6.1 (agent base), S3.1 (polygon connector), S4.2 (risk calculator) |
| Location | `agents/risk_guardian.py` |
| Test | `tests/test_risk_guardian.py` |
| Status | spec-written |

## Purpose

Implement the RiskGuardian specialist agent -- a portfolio risk management agent that fetches price history from Polygon.io via `PolygonConnector`, computes risk metrics using `risk_calculator` functions, and returns a `RiskGuardianReport` with a BUY/HOLD/SELL signal based on risk profile.

## Requirements

### R1: Agent Class -- `RiskGuardian`

Create a `RiskGuardian` class that extends `BaseAnalystAgent` from `agents/base_agent.py`.

- **agent_name**: `"risk_guardian"`
- **output_schema**: `RiskGuardianReport`
- **tools**: Wrap `PolygonConnector` and `risk_calculator` methods as ADK-compatible tool functions
- **model**: Default `"gemini-3-flash-preview"`

### R2: Tool Functions

Define standalone async tool functions that the ADK agent can invoke:

#### `get_price_history_tool(ticker: str) -> dict`
- Calls `PolygonConnector.get_price_history(ticker, days=365)`
- Returns the raw dict from Polygon (dates, closes, volumes, etc.)
- Returns `{}` on error (never raises)

#### `calc_risk_metrics_tool(ticker: str) -> dict`
- Calls `PolygonConnector.get_price_history(ticker, days=365)` to get price data
- Extracts closing prices, computes daily returns
- Calls `risk_calculator` functions: `calc_beta()`, `calc_annualized_volatility()`, `calc_sharpe()`, `calc_max_drawdown()`, `calc_var_95()`, `calc_position_size()`
- For beta: uses SPY-like market returns approximation (or uniform market assumption)
- Returns dict with all computed metrics: `beta`, `annualized_volatility`, `sharpe_ratio`, `max_drawdown`, `var_95`, `suggested_position_size`
- Returns `{}` on error (never raises)
- **Position size cap**: `calc_position_size()` already caps at 0.10

### R3: Analyze Method

The `analyze(ticker)` method is inherited from `BaseAnalystAgent`. It:
1. Sends the ticker to the ADK agent with the RiskGuardian persona
2. The LLM uses the tool functions to fetch data and compute risk metrics
3. The LLM returns a JSON response matching `RiskGuardianReport`
4. `BaseAnalystAgent.analyze()` validates the response via `RiskGuardianReport.model_validate_json()`
5. On failure, returns a fallback HOLD/0.0 report

### R4: Convenience Factory

Provide a module-level `create_risk_guardian()` factory function:
```python
def create_risk_guardian() -> RiskGuardian:
    return RiskGuardian()
```

### R5: Module-Level Instance

Provide a default instance for easy import:
```python
risk_guardian = create_risk_guardian()
```

### R6: Error Handling

- All tool functions wrap external calls in try/except
- `PolygonConnector` errors return `{}` (already handled)
- `risk_calculator` errors caught and return `{}`
- Agent-level errors caught by `BaseAnalystAgent.analyze()` fallback
- No exception propagates to the caller

## Signal Logic (from persona)

- **BUY**: Low risk profile -- low beta, low volatility, high Sharpe, manageable drawdown
- **SELL**: High risk profile -- high beta, high volatility, negative Sharpe, severe drawdown history
- **HOLD**: Moderate risk, acceptable for a diversified portfolio

## RiskGuardianReport Fields

| Field | Type | Source |
|-------|------|--------|
| ticker | str | Input |
| agent_name | str | `"risk_guardian"` |
| signal | BUY/HOLD/SELL | LLM decision |
| confidence | float [0,1] | LLM decision |
| reasoning | str | LLM explanation |
| beta | float \| None | risk_calculator.calc_beta() |
| annualized_volatility | float \| None | risk_calculator.calc_annualized_volatility() |
| sharpe_ratio | float \| None | risk_calculator.calc_sharpe() |
| max_drawdown | float \| None | risk_calculator.calc_max_drawdown() |
| suggested_position_size | float \| None | risk_calculator.calc_position_size() -- capped at 0.10 |
| var_95 | float \| None | risk_calculator.calc_var_95() |

## Test Plan

### T1: Instantiation
- `RiskGuardian` creates successfully
- `agent_name` is `"risk_guardian"`
- `output_schema` is `RiskGuardianReport`
- Tool functions are registered

### T2: Tool Functions -- get_price_history_tool
- `get_price_history_tool("AAPL")` calls `PolygonConnector.get_price_history`
- Returns `{}` on connector error

### T3: Tool Functions -- calc_risk_metrics_tool
- `calc_risk_metrics_tool("AAPL")` fetches price data and computes all risk metrics
- Returns dict with keys: beta, annualized_volatility, sharpe_ratio, max_drawdown, var_95, suggested_position_size
- `suggested_position_size` never exceeds 0.10
- Returns `{}` on error

### T4: Analyze (mocked LLM)
- Mock the ADK `Runner.run_async` to return a valid `RiskGuardianReport` JSON
- Verify the returned report has correct ticker, agent_name, signal, confidence
- Verify risk fields (beta, volatility, etc.) are populated

### T5: Analyze Fallback
- Mock the ADK runner to raise an exception
- Verify fallback report: signal=HOLD, confidence=0.0

### T6: Agent Card
- `get_agent_card()` returns dict with correct name, capabilities, output_schema

### T7: Factory Function
- `create_risk_guardian()` returns a `RiskGuardian` instance
- Module-level `risk_guardian` is a `RiskGuardian` instance

### T8: Position Size Cap
- Verify that even with very low volatility, position size is capped at 0.10
- Validator on `RiskGuardianReport.suggested_position_size` clamps to [0, 0.10]

## File Structure

```
agents/risk_guardian.py      <- Implementation
tests/test_risk_guardian.py  <- Tests (all external services mocked)
```

## Acceptance Criteria

1. `RiskGuardian` extends `BaseAnalystAgent` correctly
2. Tool functions wrap `PolygonConnector` and `risk_calculator` calls with error handling
3. `analyze("AAPL")` returns a valid `RiskGuardianReport` (with mocked LLM)
4. Fallback returns HOLD/0.0 on any error
5. `suggested_position_size` never exceeds 0.10
6. All tests pass: `pytest tests/test_risk_guardian.py -v`
7. Ruff clean: `ruff check agents/risk_guardian.py`
8. Agent card generation works correctly
