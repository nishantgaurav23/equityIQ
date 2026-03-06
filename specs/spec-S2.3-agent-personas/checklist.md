# Checklist -- Spec S2.3: Agent Personas

## Phase 1: Setup & Dependencies
- [x] No dependencies to verify (standalone module)
- [x] Create `config/analyst_personas.py`
- [x] Ensure `config/__init__.py` exists

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_analyst_personas.py`
- [x] Write failing tests for PERSONAS dict: importable, is dict, 7 keys, required keys
- [x] Write failing tests for value types: all strings, all non-empty (len > 50)
- [x] Write failing tests for content keywords: valuation ratios, confidence cap, SELL override, position limit, STRONG threshold
- [x] Write test for output schema references in each persona
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement PERSONAS dict with all 7 agent system prompts
- [x] ValuationScout: P/E, P/B, revenue growth, debt/equity, FCF yield, intrinsic value
- [x] MomentumTracker: RSI, MACD, SMA crossovers, volume trends, momentum score
- [x] PulseMonitor: sentiment, event detection, confidence cap rule (< 3 articles -> 0.70)
- [x] EconomyWatcher: GDP, inflation, Fed funds, unemployment, macro regime
- [x] ComplianceChecker: SEC filings, going_concern/restatement SELL override
- [x] SignalSynthesizer: weighted fusion, STRONG signal threshold (0.75), default weights
- [x] RiskGuardian: beta, volatility, Sharpe, drawdown, VaR, 10% position size cap
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure `config/analyst_personas.py` is importable from project root
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked (10 outcomes)
- [x] No hardcoded secrets
- [x] Update roadmap.md status: `spec-written` -> `done`
