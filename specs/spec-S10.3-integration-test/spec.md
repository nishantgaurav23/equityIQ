# Spec S10.3 -- Integration Test: Full Pipeline

## Overview

End-to-end integration test for the full EquityIQ analysis pipeline. Mocks all external services (Polygon, FRED, NewsAPI, SEC, Gemini) and submits analysis requests through the FastAPI app. Asserts correct FinalVerdict structure, all agents called, verdict stored in InsightVault, and response format correct. Also tests the portfolio endpoint end-to-end.

## Dependencies

- S10.1 (Pipeline Wiring) -- session_id threading, full pipeline flow
- S10.2 (Graceful Degradation) -- agent failure handling, confidence reduction

## Target Location

`tests/test_pipeline.py`

---

## Functional Requirements

### FR-1: Single Ticker Integration Test
- **What**: POST `/api/v1/analyze/AAPL` through the FastAPI TestClient returns a valid FinalVerdict
- **Inputs**: Ticker string via URL path
- **Outputs**: JSON response with FinalVerdict schema (ticker, final_signal, overall_confidence, session_id, key_drivers, analyst_signals, risk_summary)
- **Assertions**:
  - Response status 200
  - `verdict.ticker == "AAPL"`
  - `verdict.final_signal` is one of STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
  - `verdict.overall_confidence` is in [0.0, 1.0]
  - `verdict.session_id` is a valid UUID string
  - `verdict.analyst_signals` contains entries from all 5 directional agents

### FR-2: All Agents Called
- **What**: Verify all 6 specialist agents (5 directional + RiskGuardian) are invoked during analysis
- **Assertions**: Each agent's `analyze()` method is called exactly once with the correct ticker
- **Approach**: Mock each agent's `analyze()` and verify call counts

### FR-3: Verdict Stored in InsightVault
- **What**: After analysis, the verdict is persisted via `InsightVault.store_verdict()`
- **Assertions**:
  - `vault.store_verdict` is called with the FinalVerdict
  - Stored verdict has the same session_id as the response
  - `GET /api/v1/verdict/{session_id}` retrieves the stored verdict

### FR-4: Portfolio Integration Test
- **What**: POST `/api/v1/portfolio` with multiple tickers returns PortfolioInsight
- **Inputs**: JSON body `{"tickers": ["AAPL", "MSFT", "GOOGL"]}`
- **Outputs**: PortfolioInsight with tickers, verdicts, portfolio_signal, diversification_score, top_pick
- **Assertions**:
  - Response status 200
  - All 3 tickers present in response
  - Each verdict is a valid FinalVerdict
  - `portfolio_signal` is a valid signal string
  - `diversification_score` is in [0.0, 1.0]

### FR-5: Session ID Consistency
- **What**: Session ID generated at the API layer is threaded through to the stored verdict
- **Assertions**:
  - Response verdict contains a session_id
  - InsightVault.store_verdict received the same session_id
  - GET /api/v1/verdict/{session_id} returns the same verdict

### FR-6: Graceful Degradation in Integration
- **What**: When one agent fails during integration test, the pipeline still returns a valid verdict
- **Inputs**: Mock one directional agent to raise an exception
- **Assertions**:
  - Response status 200 (not 500)
  - Verdict overall_confidence is reduced (by 0.20)
  - key_drivers contains a WARNING entry for the failed agent
  - Signal is still valid (STRONG signals downgraded if confidence < 0.75)

### FR-7: Error Handling Integration
- **What**: Invalid requests return proper error responses
- **Assertions**:
  - POST `/api/v1/analyze/` with empty ticker -> 422 or 404
  - POST `/api/v1/analyze/TOOLONGTICKER123` with too-long ticker -> 400 InvalidTickerError
  - POST `/api/v1/portfolio` with empty tickers list -> 422

---

## Tangible Outcomes

- [ ] **Outcome 1**: `pytest tests/test_pipeline.py -v` passes with all tests green
- [ ] **Outcome 2**: Single ticker analysis returns valid FinalVerdict with all required fields
- [ ] **Outcome 3**: All 6 agents are verified to be called during analysis
- [ ] **Outcome 4**: Verdict is stored and retrievable by session_id
- [ ] **Outcome 5**: Portfolio endpoint returns valid PortfolioInsight for multiple tickers
- [ ] **Outcome 6**: Pipeline degrades gracefully when agents fail
- [ ] **Outcome 7**: Error cases return proper HTTP error codes

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)

1. **test_analyze_single_ticker_returns_valid_verdict**: POST /analyze/AAPL -> 200, valid FinalVerdict
2. **test_all_agents_called_during_analysis**: Verify each agent's analyze() called once
3. **test_verdict_stored_in_vault**: Verdict stored and retrievable by session_id
4. **test_session_id_consistency**: API session_id matches stored verdict session_id
5. **test_portfolio_analysis_returns_valid_insight**: POST /portfolio with 3 tickers -> 200, valid PortfolioInsight
6. **test_portfolio_all_tickers_analyzed**: Each ticker in portfolio gets its own verdict
7. **test_graceful_degradation_single_agent_failure**: One agent fails -> still returns verdict with reduced confidence
8. **test_graceful_degradation_warning_in_key_drivers**: Failed agent produces WARNING in key_drivers
9. **test_invalid_ticker_returns_error**: Too-long ticker -> 400
10. **test_empty_portfolio_returns_error**: Empty tickers list -> 422

### Mocking Strategy

- **All 6 agents**: Mock `analyze()` on each agent class to return pre-built report fixtures
- **InsightVault**: Use real in-memory SQLite vault (initialized via lifespan) or mock store_verdict
- **No external HTTP calls**: All Polygon, FRED, NewsAPI, SEC, Gemini calls are behind agent mocks
- **FastAPI TestClient**: Use `httpx.AsyncClient` with `ASGITransport` for async test support
- Use `unittest.mock.patch` to mock agent loading in MarketConductor._lazy_load_agents()

### Coverage Expectation

- All 7 FRs covered by at least one test
- Edge cases: agent failure, invalid input, empty portfolio

---

## References

- `specs/spec-S10.1-pipeline-wiring/spec.md` -- pipeline wiring and session threading
- `specs/spec-S10.2-graceful-degradation/spec.md` -- degradation behavior
- `api/routes.py` -- API endpoints under test
- `agents/market_conductor.py` -- orchestrator
- `config/data_contracts.py` -- FinalVerdict, PortfolioInsight schemas
- `roadmap.md`, `design.md`
