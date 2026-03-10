# Spec S10.1 -- Pipeline Wiring

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S10.1 |
| Phase | 10 -- Pipeline Integration |
| Depends On | S9.1 (analyze endpoint), S8.2 (market conductor), S5.1 (insight vault) |
| Location | `app.py`, `api/routes.py`, `agents/market_conductor.py`, `agents/signal_synthesizer.py`, `models/signal_fusion.py` |
| Status | pending |

## Problem

The analysis pipeline is functionally wired (request -> conductor -> agents -> synthesizer -> vault -> response) but session tracing is incomplete:

1. **Session ID generated in wrong layer**: `SignalFusionModel.predict()` unconditionally generates a new UUID, so the API layer cannot correlate request with stored verdict.
2. **No request-level session ID**: API endpoints don't generate a session_id at entry; it's created deep in the ML layer.
3. **No threading**: Session ID is not passed through API -> conductor -> synthesizer -> vault chain.
4. **Portfolio sessions**: Each ticker in a portfolio request gets an unrelated session_id; no parent session concept.

## Solution

Move session_id generation to the API entry point and thread it through every layer. Each layer accepts an optional `session_id` parameter; if provided, it is reused (never regenerated).

## Functional Requirements

### FR-1: Request-Level Session ID Generation

- `api/routes.py` `analyze_ticker()` generates `session_id = str(uuid.uuid4())` at entry.
- `analyze_portfolio()` generates a parent `session_id` and passes it to each individual `conductor.analyze()` call.
- Session ID is included in log messages at API layer.

### FR-2: MarketConductor Session Threading

- `MarketConductor.analyze(ticker, session_id=None)` accepts optional session_id.
- If session_id is provided, it is threaded to synthesizer and vault.
- If session_id is None (direct call without API), conductor generates one.
- All conductor-level logs include session_id.

### FR-3: SignalSynthesizer Session Threading

- `SignalSynthesizer.synthesize(reports, risk_report=None, session_id=None)` accepts optional session_id.
- Passes session_id to `SignalFusionModel.predict()`.

### FR-4: SignalFusionModel Session ID Fix

- `SignalFusionModel.predict(reports, session_id=None)` accepts optional session_id.
- If session_id is provided, uses it instead of generating a new UUID.
- If session_id is None, generates UUID as fallback (backward compat).

### FR-5: Verdict Completeness

- After synthesis, `conductor.analyze()` ensures:
  - `verdict.session_id` matches the request session_id.
  - `verdict.ticker` is set to the requested ticker (already done).
- The stored verdict in InsightVault has the same session_id as the API response.

### FR-6: Response Session ID

- API response JSON includes `session_id` that can be used to retrieve the verdict via `GET /api/v1/verdict/{session_id}`.
- Portfolio response includes the parent session_id.

### FR-7: Logging Correlation

- All layers log with session_id for request tracing.
- Format: `logger.info("...", extra={"session_id": session_id})` or inline in message.

## Non-Functional Requirements

- No new dependencies.
- All existing tests must continue to pass (backward-compatible changes).
- session_id parameter is always optional with sensible defaults.

## API Contract Changes

### Modified: `MarketConductor.analyze()`
```python
# Before
async def analyze(self, ticker: str) -> FinalVerdict:

# After
async def analyze(self, ticker: str, session_id: str | None = None) -> FinalVerdict:
```

### Modified: `SignalSynthesizer.synthesize()`
```python
# Before
async def synthesize(self, reports, risk_report=None) -> FinalVerdict:

# After
async def synthesize(self, reports, risk_report=None, session_id: str | None = None) -> FinalVerdict:
```

### Modified: `SignalFusionModel.predict()`
```python
# Before
def predict(self, reports: list) -> FinalVerdict:

# After
def predict(self, reports: list, session_id: str | None = None) -> FinalVerdict:
```

## Test Strategy

- Unit tests for session_id threading at each layer.
- Verify session_id consistency: API entry -> conductor -> synthesizer -> vault -> response.
- Verify backward compatibility: calling without session_id still works.
- Verify portfolio parent session_id flow.
- All external services mocked.

## Files Changed

| File | Change |
|------|--------|
| `api/routes.py` | Generate session_id at entry, pass to conductor |
| `agents/market_conductor.py` | Accept session_id param, thread to synthesizer |
| `agents/signal_synthesizer.py` | Accept session_id param, thread to fusion model |
| `models/signal_fusion.py` | Accept session_id param, use if provided |
| `tests/test_pipeline_wiring.py` | New: session_id threading tests |
| Existing test files | Update mocks for new signatures |

## Out of Scope

- S9.4 (error taxonomy) -- separate spec.
- S10.2 (graceful degradation) -- separate spec.
- S10.3 (full integration test) -- separate spec.
