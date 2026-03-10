# Spec S8.1 -- Signal Synthesizer Agent

## Overview
ADK-based agent that receives 5 AnalystReports (ValuationReport, MomentumReport, PulseReport, EconomyReport, ComplianceReport) plus a RiskGuardianReport, runs XGBoost signal fusion via `SignalFusionModel`, applies compliance hard override, and returns a `FinalVerdict`. Runs on port 8006.

## Dependencies
- S6.1 (agent base class -- `BaseAnalystAgent`)
- S4.1 (signal fusion model -- `SignalFusionModel`)
- S2.2 (verdict schemas -- `FinalVerdict`, `RiskGuardianReport`)

## Target Location
`agents/signal_synthesizer.py`

---

## Functional Requirements

### FR-1: Agent construction
- **What**: `SignalSynthesizer` extends `BaseAnalystAgent` with `agent_name="signal_synthesizer"`, `output_schema=FinalVerdict`, and tool functions that wrap `SignalFusionModel` operations.
- **Inputs**: Optional `model` param (LLM model name, default `gemini-3-flash-preview`).
- **Outputs**: Fully initialized agent with ADK Agent, persona from PERSONAS dict.
- **Edge cases**: Missing persona key raises `KeyError` (inherited from `BaseAnalystAgent`).

### FR-2: Synthesize tool function
- **What**: A module-level async tool function `synthesize_signals(reports_json: str) -> dict` that:
  1. Parses JSON string into a list of typed AnalystReport subclasses.
  2. Instantiates or reuses a `SignalFusionModel`.
  3. Calls `model.predict(reports)` to get `FinalVerdict`.
  4. Returns the verdict as a dict.
- **Inputs**: JSON string containing serialized analyst reports.
- **Outputs**: Dict representation of `FinalVerdict`.
- **Edge cases**: Invalid JSON -> return fallback HOLD verdict. Empty reports list -> HOLD with confidence 0.0.

### FR-3: Direct synthesize method (non-LLM path)
- **What**: `SignalSynthesizer.synthesize(reports, risk_report=None) -> FinalVerdict` that bypasses the LLM and directly uses `SignalFusionModel.predict()`. This is the primary path used by `MarketConductor` for deterministic signal fusion.
- **Inputs**: List of `AnalystReport` subclasses, optional `RiskGuardianReport`.
- **Outputs**: `FinalVerdict` with risk_summary populated from `RiskGuardianReport` if provided.
- **Edge cases**: Empty reports -> HOLD/0.0. All agents missing -> HOLD/0.0. Single report -> reduced confidence.

### FR-4: Risk summary integration
- **What**: When a `RiskGuardianReport` is provided to `synthesize()`, populate `FinalVerdict.risk_summary` with a formatted string including beta, volatility, max_drawdown, and suggested_position_size.
- **Inputs**: `RiskGuardianReport` (optional).
- **Outputs**: `risk_summary` field set on FinalVerdict.
- **Edge cases**: None risk_report -> risk_summary stays empty string.

### FR-5: Weight adjustment for macro regime
- **What**: Before prediction, if an `EconomyReport` is present with `macro_regime` of "contraction" or "stagflation", adjust weights to increase EconomyWatcher to 0.30 (redistributing from others proportionally).
- **Inputs**: List of reports (check for EconomyReport with regime).
- **Outputs**: Adjusted weights passed to `SignalFusionModel`.
- **Edge cases**: No EconomyReport or neutral regime -> use default weights.

### FR-6: Compliance hard override
- **What**: If `ComplianceReport` has `going_concern` or `restatement` in `risk_flags`, the final signal MUST be SELL regardless of XGBoost/weighted-average output. Delegated to `SignalFusionModel.apply_compliance_override()`.
- **Inputs**: Compliance report within the reports list.
- **Outputs**: FinalVerdict with signal forced to SELL.
- **Edge cases**: No ComplianceReport -> no override applied.

### FR-7: Factory function and module-level instance
- **What**: `create_signal_synthesizer() -> SignalSynthesizer` factory and `signal_synthesizer` module-level singleton, matching the pattern in other agent modules.
- **Inputs**: None.
- **Outputs**: Ready-to-use `SignalSynthesizer` instance.

### FR-8: Graceful error handling
- **What**: All external calls (LLM, model prediction) wrapped in try/except. On failure, return a safe HOLD/0.0 FinalVerdict. Never crash.
- **Inputs**: Any exception during synthesis.
- **Outputs**: Fallback FinalVerdict.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `agents/signal_synthesizer.py` exists with `SignalSynthesizer` class extending `BaseAnalystAgent`
- [ ] **Outcome 2**: `synthesize()` method produces correct `FinalVerdict` from 5 analyst reports
- [ ] **Outcome 3**: Compliance override forces SELL when `going_concern` or `restatement` present
- [ ] **Outcome 4**: Weight adjustment activates for contraction/stagflation macro regimes
- [ ] **Outcome 5**: Risk summary populated from `RiskGuardianReport` when provided
- [ ] **Outcome 6**: Empty/missing reports produce HOLD with confidence 0.0
- [ ] **Outcome 7**: Errors in synthesis produce fallback HOLD/0.0 verdict (never crashes)
- [ ] **Outcome 8**: Module exports `signal_synthesizer` singleton and `create_signal_synthesizer()` factory

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_signal_synthesizer_construction**: Verify class instantiation, agent_name, output_schema
2. **test_synthesize_all_reports_buy**: 5 BUY reports -> BUY or STRONG_BUY verdict
3. **test_synthesize_all_reports_sell**: 5 SELL reports -> SELL or STRONG_SELL verdict
4. **test_synthesize_mixed_reports**: Mixed signals -> appropriate weighted result
5. **test_synthesize_empty_reports**: Empty list -> HOLD with confidence 0.0
6. **test_compliance_override_going_concern**: going_concern flag -> forces SELL
7. **test_compliance_override_restatement**: restatement flag -> forces SELL
8. **test_compliance_override_no_flags**: Clean compliance -> no override
9. **test_risk_summary_integration**: RiskGuardianReport -> risk_summary populated
10. **test_risk_summary_none**: No risk report -> risk_summary empty
11. **test_weight_adjustment_contraction**: Contraction regime -> EconomyWatcher weight 0.30
12. **test_weight_adjustment_stagflation**: Stagflation regime -> EconomyWatcher weight 0.30
13. **test_weight_adjustment_expansion**: Expansion regime -> default weights
14. **test_synthesize_missing_agents**: Only 3 of 5 reports -> reduced confidence
15. **test_synthesize_error_handling**: Exception in model -> fallback HOLD/0.0
16. **test_factory_function**: `create_signal_synthesizer()` returns correct type
17. **test_module_singleton**: `signal_synthesizer` module-level instance exists

### Mocking Strategy
- Mock `google.adk` (Agent, Runner, InMemorySessionService) -- inherited from BaseAnalystAgent
- Mock `SignalFusionModel` only when testing error paths; use real model for integration tests
- Use `pytest-asyncio` for async test support

### Coverage Expectation
- All public methods and the factory function have at least one test
- Edge cases: empty reports, missing agents, compliance overrides, error paths

---

## References
- roadmap.md (Phase 8 -- Orchestration)
- design.md (signal fusion flow)
- `models/signal_fusion.py` (SignalFusionModel)
- `agents/base_agent.py` (BaseAnalystAgent)
- `config/data_contracts.py` (FinalVerdict, AnalystReport subclasses)
- `config/analyst_personas.py` (PERSONAS["signal_synthesizer"])
