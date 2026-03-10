# S15.2 -- Rich Analysis Response

## Feature
Surface full agent reports in API response.

## Location
- `config/data_contracts.py`
- `agents/market_conductor.py`
- `api/routes.py`

## Depends On
- S8.2 (market conductor)
- S2.2 (verdict schemas)

## Description
Enhance `FinalVerdict` to include `analyst_details` (per-agent structured data with
signal, confidence, reasoning, key_metrics, data_source, execution_time_ms). Add
`risk_level` (LOW/MEDIUM/HIGH) and total `execution_time_ms`. `MarketConductor.analyze()`
populates these fields from actual agent reports. Risk level calculated from signal
disagreement and average confidence.

## Risk Level Calculation

| Condition | Risk Level |
|-----------|------------|
| signal std > 0.6 OR avg confidence < 0.40 | **HIGH** |
| signal std > 0.3 OR avg confidence < 0.60 | **MEDIUM** |
| otherwise | **LOW** |

## Acceptance Criteria

1. `FinalVerdict.analyst_details` populated with per-agent data
2. Each agent detail includes: signal, confidence, reasoning, key_metrics dict, data_source, execution_time_ms
3. `FinalVerdict.risk_level` computed from agent signals
4. `FinalVerdict.execution_time_ms` tracks total analysis time
5. Backward compatible -- `analyst_signals` dict still works
6. Tests verify risk level calculation, detail population, timing
