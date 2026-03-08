# S7.6 -- RiskGuardian Checklist

## Implementation Progress

- [x] Create `agents/risk_guardian.py`
- [x] Define `get_price_history_tool()` async tool function
- [x] Define `calc_risk_metrics_tool()` async tool function
- [x] Implement `RiskGuardian` class extending `BaseAnalystAgent`
- [x] Add `create_risk_guardian()` factory function
- [x] Add module-level `risk_guardian` instance
- [x] Create `tests/test_risk_guardian.py`
- [x] T1: Test instantiation and properties
- [x] T2: Test get_price_history_tool (mocked connector)
- [x] T3: Test calc_risk_metrics_tool (mocked connector + calculator)
- [x] T4: Test analyze with mocked LLM response
- [x] T5: Test analyze fallback on error
- [x] T6: Test agent card generation
- [x] T7: Test factory function and module instance
- [x] T8: Test position size cap enforcement
- [x] All tests passing (25/25)
- [x] Ruff lint clean
- [x] Checklist complete
