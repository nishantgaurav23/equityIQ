# Spec S8.2 -- Market Conductor (Orchestrator Agent)

## Meta

| Field | Value |
|-------|-------|
| Spec ID | S8.2 |
| Phase | 8 -- Orchestration |
| Location | `agents/market_conductor.py` |
| Depends On | S6.2 (A2A server), S7.1-S7.6 (all specialist agents), S8.1 (signal synthesizer), S5.1 (insight vault) |
| Status | spec-written |

## Overview

The MarketConductor is the orchestrator agent that coordinates all 6 specialist agents + SignalSynthesizer. It dispatches analysis requests to all agents via `asyncio.gather()`, collects results, feeds them through SignalSynthesizer for signal fusion, stores the verdict in InsightVault, and returns a FinalVerdict. Port 8000.

## Functional Requirements

### FR-1: Initialization

- `MarketConductor.__init__(vault: InsightVault | None = None, timeout: float = 30.0)`
- Accepts optional InsightVault for verdict persistence
- Accepts optional per-agent timeout (default 30s)
- Lazy-loads agents on first `analyze()` call to avoid module-level ADK init issues
- Creates a SignalSynthesizer instance for signal fusion

### FR-2: Agent Lazy Loading

- `_lazy_load_agents()` imports and instantiates all 6 specialist agents:
  - ValuationScout, MomentumTracker, PulseMonitor, EconomyWatcher, ComplianceChecker, RiskGuardian
- Each agent import wrapped in try/except -- failed imports are logged and skipped
- Agent list is cached after first load (subsequent calls return same list)

### FR-3: Parallel Analysis

- `async analyze(ticker: str) -> FinalVerdict`
- Normalizes ticker (strip + uppercase)
- Runs all agents in parallel via `asyncio.gather(*tasks, return_exceptions=True)`
- Per-agent timeout of 30s (configurable) using `asyncio.wait_for()`
- Returns HOLD/0.0 if no agents are available

### FR-4: Result Processing

- Separates successful AnalystReports from exceptions
- RiskGuardianReport is separated (not included in signal fusion)
- 5 directional reports fed to SignalSynthesizer.synthesize()
- Risk report attached as risk_summary string on the verdict

### FR-5: Graceful Degradation

- Agent exceptions are logged but never crash the conductor
- Each missing/failed agent is tracked
- Missing agents reduce confidence (handled by SignalFusionModel's MISSING_AGENT_PENALTY)

### FR-6: Verdict Storage

- If InsightVault is provided, store verdict after fusion
- Vault failures are logged but never crash the conductor
- session_id is assigned to the verdict

### FR-7: Agent Name Mapping

- Internal agent names (snake_case) are mapped to display names (PascalCase) for SignalFusionModel compatibility
- Map: valuation_scout -> ValuationScout, momentum_tracker -> MomentumTracker, etc.

### FR-8: A2A Server

- `create_conductor_server()` factory returns a FastAPI app using `create_agent_server()`
- Port 8000
- Exposes /.well-known/agent-card.json, /a2a (JSONRPC), /health

## Non-Functional Requirements

- All external calls wrapped in try/except (never crash)
- Async everywhere (async def, await)
- Logging via Python logging module
- Type hints on all public methods

## Test Requirements

- Test init with and without vault
- Test ticker normalization
- Test no-agents returns HOLD/0.0
- Test agent exception is gracefully handled
- Test verdict stored in vault
- Test vault failure doesn't crash
- Test risk summary attached from RiskGuardian
- Test compliance override propagated through SignalSynthesizer
- Test lazy load caching
- Test per-agent timeout handling
- Test all agents called in parallel (asyncio.gather)
- All agents mocked (no real ADK/LLM calls)

## Acceptance Criteria

1. `MarketConductor` class with `analyze(ticker)` method
2. All 6 specialist agents dispatched in parallel
3. SignalSynthesizer used for signal fusion (not raw SignalFusionModel)
4. RiskGuardian report attached as risk_summary
5. Compliance override applied (going_concern/restatement -> SELL)
6. InsightVault integration for verdict persistence
7. Graceful degradation on agent failures
8. Per-agent timeout (30s default)
9. All tests pass, ruff clean
