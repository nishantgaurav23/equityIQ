# Spec S7.5 -- Compliance Checker

## Overview
Regulatory risk agent that uses SecConnector to analyze SEC filings and detect compliance risks. Returns a ComplianceReport with BUY/HOLD/SELL signal. Critically, if `going_concern` or `restatement` is detected in risk_flags, the signal **MUST** be SELL -- this is a hard override safety rule. Runs on port 8005.

## Dependencies
- **S6.1** -- BaseAnalystAgent (agent base class)
- **S3.4** -- SecConnector (SEC Edgar wrapper with risk scoring)

## Target Location
- `agents/compliance_checker.py`
- `tests/test_compliance_checker.py`

---

## Functional Requirements

### FR-1: Tool Functions
- **What**: Module-level async tool functions wrapping SecConnector for ADK agent use
- **Functions**:
  - `get_sec_filings_tool(ticker: str) -> dict` -- calls `_sec_connector.get_sec_filings(ticker)`, returns list of filings or `{}` on error
  - `score_risk_tool(ticker: str) -> dict` -- calls `_sec_connector.score_risk(ticker)`, returns risk assessment dict or `{}` on error
- **Error handling**: try/except wraps each call, returns `{}` on any exception, never raises
- **Connector**: Module-level `_sec_connector = SecConnector()` instance shared across calls

### FR-2: ComplianceCheckerAgent Class
- **What**: Specialist agent class extending BaseAnalystAgent
- **Init**: `agent_name="compliance_checker"`, `output_schema=ComplianceReport`, `tools=[get_sec_filings_tool, score_risk_tool]`, `model="gemini-3-flash-preview"`
- **Inherits**: `analyze()`, `get_agent_card()`, `_fallback_report()` from BaseAnalystAgent
- **Persona**: Loaded from `PERSONAS["compliance_checker"]` via base class

### FR-3: Factory Function and Module Export
- **What**: `create_compliance_checker()` factory and module-level `compliance_checker` instance
- **Pattern**: Matches other agents (valuation_scout, momentum_tracker, pulse_monitor)

### FR-4: Going Concern / Restatement Hard Override
- **What**: The ComplianceChecker persona instructs the LLM to always emit SELL when `going_concern` or `restatement` appears in risk_flags. This is enforced at the persona/prompt level (not in Python code), but the test suite must verify the contract by checking that ComplianceReport allows SELL signal when these flags are present.
- **Rule**: This is a project-wide hard rule -- going_concern or restatement always forces SELL override.

### FR-5: Agent Card Generation
- **What**: `get_agent_card()` returns A2A-compatible discovery card
- **Fields**: name="compliance_checker", output_schema="ComplianceReport", capabilities include tool function names, URL from settings.COMPLIANCE_AGENT_URL

---

## Tangible Outcomes

- [ ] **Outcome 1**: `agents/compliance_checker.py` exists with ComplianceCheckerAgent class
- [ ] **Outcome 2**: `get_sec_filings_tool()` calls SecConnector and returns filings dict
- [ ] **Outcome 3**: `score_risk_tool()` calls SecConnector and returns risk dict
- [ ] **Outcome 4**: Both tool functions return `{}` on error, never raise
- [ ] **Outcome 5**: Agent uses ComplianceReport output schema
- [ ] **Outcome 6**: Agent has 2 tools registered
- [ ] **Outcome 7**: `create_compliance_checker()` factory returns valid agent
- [ ] **Outcome 8**: Module-level `compliance_checker` instance is ready to use
- [ ] **Outcome 9**: `analyze()` returns ComplianceReport on success (mocked LLM)
- [ ] **Outcome 10**: `analyze()` returns safe fallback (HOLD, 0.0) on error
- [ ] **Outcome 11**: Agent card includes correct name, schema, and capabilities
- [ ] **Outcome 12**: All tests pass: `python -m pytest tests/test_compliance_checker.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)

1. **test_get_sec_filings_tool_success**: Mock _sec_connector, verify tool returns filings
2. **test_get_sec_filings_tool_error**: Mock _sec_connector to raise, verify returns {}
3. **test_get_sec_filings_tool_never_raises**: Confirm no exception escapes
4. **test_score_risk_tool_success**: Mock _sec_connector, verify tool returns risk dict
5. **test_score_risk_tool_error**: Mock _sec_connector to raise, verify returns {}
6. **test_score_risk_tool_never_raises**: Confirm no exception escapes
7. **test_instantiation**: ComplianceCheckerAgent() creates with name="compliance_checker"
8. **test_output_schema**: Agent uses ComplianceReport
9. **test_inherits_base**: Subclass of BaseAnalystAgent
10. **test_has_two_tools**: Agent has exactly 2 tools
11. **test_card_has_name**: Agent card name is "compliance_checker"
12. **test_card_has_output_schema**: Agent card output_schema is "ComplianceReport"
13. **test_card_has_capabilities**: Agent card lists both tool functions
14. **test_module_level_instance**: `compliance_checker` exists and has correct name
15. **test_factory_function**: `create_compliance_checker()` returns valid agent
16. **test_analyze_returns_compliance_report**: Mocked LLM returns valid ComplianceReport
17. **test_fallback_on_error**: LLM failure returns HOLD/0.0 fallback
18. **test_fallback_never_raises**: analyze() never raises even on crash
19. **test_compliance_report_sell_with_going_concern**: ComplianceReport validates with going_concern + SELL
20. **test_compliance_report_sell_with_restatement**: ComplianceReport validates with restatement + SELL
21. **test_risk_score_clamped**: ComplianceReport risk_score clamped to [0.0, 1.0]

### Mocking Strategy
- `_sec_connector`: patch at `agents.compliance_checker._sec_connector`
- LLM/Runner: patch `agents.base_agent.Runner` and `agents.base_agent.InMemorySessionService`
- No real API calls in tests

### Coverage Expectation
- All public functions and class methods tested
- Error paths tested for both tool functions
- ComplianceReport schema validation tested

---

## References
- `roadmap.md` -- S7.5 spec definition
- `config/data_contracts.py` -- ComplianceReport schema
- `config/analyst_personas.py` -- compliance_checker persona
- `tools/sec_connector.py` -- SecConnector class
- `agents/base_agent.py` -- BaseAnalystAgent base class
- `agents/pulse_monitor.py` -- Reference implementation (same pattern)
