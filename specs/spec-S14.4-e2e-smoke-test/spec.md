# Spec S14.4 -- End-to-End Smoke Test

## Overview
Full end-to-end smoke test that exercises the entire EquityIQ analysis pipeline for AAPL with all external APIs mocked. Asserts a complete FinalVerdict is returned within 30 seconds. Unlike the integration test (S10.3), this smoke test validates the complete user-facing flow including response structure richness, timing constraints, and all FinalVerdict fields populated.

## Dependencies
- S10.1 (Pipeline Wiring) -- full analysis pipeline must be wired

## Target Location
- `tests/test_e2e.py`

---

## Functional Requirements

### FR-1: Full AAPL Analysis Smoke Test
- **What**: POST `/api/v1/analyze/AAPL` returns a complete FinalVerdict with all expected fields populated
- **Inputs**: Ticker "AAPL" via POST request
- **Outputs**: FinalVerdict JSON with: ticker, final_signal (5-level), overall_confidence [0,1], analyst_signals (5 agents), analyst_details (per-agent breakdown), risk_summary, key_drivers, session_id, execution_time_ms, timestamp
- **Edge cases**: Ensure no field is missing or null when all agents succeed

### FR-2: Response Time Under 30 Seconds
- **What**: The full analysis pipeline completes within 30 seconds wall-clock time
- **Inputs**: POST `/api/v1/analyze/AAPL`
- **Outputs**: Response received in <30s
- **Edge cases**: Mocked APIs should be near-instant; this validates no accidental blocking

### FR-3: All Agent Signals Present
- **What**: The returned FinalVerdict includes signals from all 5 directional agents
- **Inputs**: FinalVerdict response
- **Outputs**: analyst_signals dict contains keys for valuation_scout, momentum_tracker, pulse_monitor, economy_watcher, compliance_checker
- **Edge cases**: Each signal is one of BUY/HOLD/SELL

### FR-4: Verdict Stored in Memory
- **What**: After analysis, the verdict is stored in InsightVault and retrievable via history endpoint
- **Inputs**: session_id from the analyze response
- **Outputs**: GET `/api/v1/history/{session_id}` returns the stored verdict
- **Edge cases**: session_id is a valid UUID

### FR-5: Health Endpoint Returns OK
- **What**: GET `/health` returns status "ok" confirming the app is running
- **Inputs**: GET request to /health
- **Outputs**: JSON with status="ok"

### FR-6: Agent Details Populated
- **What**: analyst_details dict contains structured AgentDetail entries for each agent
- **Inputs**: FinalVerdict response
- **Outputs**: Each AgentDetail has agent_name, signal, confidence, reasoning
- **Edge cases**: confidence values are all in [0,1]

### FR-7: Compliance Override Smoke Test
- **What**: When ComplianceChecker flags going_concern, final signal is forced to SELL
- **Inputs**: Mock ComplianceChecker to return going_concern risk flag
- **Outputs**: FinalVerdict.final_signal is SELL or STRONG_SELL
- **Edge cases**: Even if all other agents say BUY

### FR-8: Portfolio Smoke Test
- **What**: POST `/api/v1/portfolio` with multiple tickers returns PortfolioInsight
- **Inputs**: {"tickers": ["AAPL", "GOOGL"]}
- **Outputs**: PortfolioInsight with verdicts for both tickers, portfolio_signal, diversification_score
- **Edge cases**: Both tickers analyzed successfully

---

## Tangible Outcomes

- [ ] **Outcome 1**: `tests/test_e2e.py` exists with 8+ test functions covering all FRs
- [ ] **Outcome 2**: Full AAPL analysis returns valid FinalVerdict in <30s (mocked)
- [ ] **Outcome 3**: All 5 agent signals present in response
- [ ] **Outcome 4**: Verdict stored and retrievable via history API
- [ ] **Outcome 5**: Compliance override (going_concern) forces SELL
- [ ] **Outcome 6**: Portfolio endpoint returns valid PortfolioInsight
- [ ] **Outcome 7**: All tests pass: `python -m pytest tests/test_e2e.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_health_endpoint_returns_ok**: GET /health returns 200 with status "ok"
2. **test_full_aapl_analysis_returns_verdict**: POST /api/v1/analyze/AAPL returns 200 with valid FinalVerdict
3. **test_response_time_under_30s**: Measure wall-clock time, assert < 30s
4. **test_all_agent_signals_present**: Verify all 5 directional agents in analyst_signals
5. **test_agent_details_populated**: Verify analyst_details has structured entries
6. **test_verdict_confidence_in_range**: overall_confidence is in [0.0, 1.0]
7. **test_verdict_has_session_id**: session_id is non-empty valid UUID
8. **test_verdict_stored_in_vault**: Retrieve stored verdict via history endpoint
9. **test_compliance_going_concern_forces_sell**: going_concern flag -> SELL override
10. **test_portfolio_smoke**: POST /api/v1/portfolio returns valid PortfolioInsight

### Mocking Strategy
- All external services mocked: Polygon, FRED, NewsAPI, SEC Edgar, Gemini
- Mock at agent level (agent.analyze returns pre-built reports) as done in test_pipeline.py
- Use patch on `MarketConductor._lazy_load_agents` to inject mock agents

### Coverage Expectation
- All 8 FRs covered with dedicated tests
- Edge cases: compliance override, portfolio multi-ticker

---

## References
- roadmap.md (S14.4 entry)
- tests/test_pipeline.py (S10.3 -- pattern to follow for mocking)
- config/data_contracts.py (FinalVerdict, PortfolioInsight schemas)
- api/routes.py (endpoint definitions)
- agents/market_conductor.py (orchestrator)
