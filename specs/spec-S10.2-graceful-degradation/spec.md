# Spec S10.2 -- Graceful Degradation

## Context
MarketConductor orchestrates 5 directional agents + RiskGuardian in parallel via `asyncio.gather()`. When agents fail or timeout, the system must degrade gracefully: partial results with reduced confidence, warning messages, and never crash.

**Location:** `agents/market_conductor.py`
**Depends on:** S10.1 (Pipeline Wiring)

## Current State
MarketConductor already handles:
- Per-agent timeout via `asyncio.wait_for` (default 30s)
- Agent exceptions caught via `return_exceptions=True` in `asyncio.gather`
- Skips failed agents and passes remaining reports to SignalSynthesizer

What's missing:
- Explicit confidence reduction of 0.20 per missing agent (applied post-synthesis)
- Warning metadata in FinalVerdict indicating which agents failed/timed out
- Partial result reporting with degradation info
- Portfolio-level graceful degradation (individual ticker failure in portfolio)

## Functional Requirements

### FR-1: Confidence Reduction for Missing Agents
When an agent fails or times out, reduce the final `overall_confidence` by 0.20 per missing directional agent (not RiskGuardian, which is informational only).

- Applied post-synthesis (after SignalSynthesizer returns verdict)
- Clamped to [0.0, 1.0]
- If confidence drops below threshold, STRONG_BUY/STRONG_SELL downgrade to BUY/SELL

### FR-2: Warning Metadata
Track which agents failed and why:

- `key_drivers` should include entries like "WARNING: ValuationScout timed out" or "WARNING: MomentumTracker failed: <error>"
- Log warnings for each failed agent (already done in current code)

### FR-3: Partial Results Still Returned
Even with 0 successful directional agents:
- Return HOLD/0.0 verdict (already handled for no-agents case)
- If at least 1 directional agent succeeds, synthesize with available reports
- RiskGuardian failure should NOT reduce directional confidence (it's informational)

### FR-4: Timeout Handling
- Per-agent timeout (default 30s) already implemented
- Timeout treated same as exception (agent skipped, confidence reduced)
- Timeout is distinguishable in warnings: "timed out after 30.0s" vs "failed: <error>"

### FR-5: Portfolio Graceful Degradation
In `analyze_portfolio()`:
- Individual ticker analysis failure -> skip ticker, continue others
- Failed tickers NOT included in PortfolioInsight.tickers
- Log which tickers failed
- If ALL tickers fail -> return PortfolioInsight with empty verdicts, HOLD signal

### FR-6: Signal Downgrade on Low Confidence
After confidence reduction:
- If `overall_confidence < 0.75` and signal is STRONG_BUY -> downgrade to BUY
- If `overall_confidence < 0.75` and signal is STRONG_SELL -> downgrade to SELL
- This enforces the rule: STRONG signals require confidence >= 0.75

## Non-Functional Requirements

- NFR-1: All external API call failures must be caught (never crash the conductor)
- NFR-2: Degradation must be transparent (warnings in key_drivers)
- NFR-3: Performance not affected when all agents succeed (penalty is 0 for 0 missing)

## Test Plan
1. All agents succeed -> no confidence reduction, no warnings
2. 1 directional agent fails -> confidence reduced by 0.20, warning in key_drivers
3. 2 directional agents fail -> confidence reduced by 0.40
4. All directional agents fail -> HOLD/0.0
5. Only RiskGuardian fails -> no confidence reduction to directional signal
6. Agent timeout -> same as failure (confidence reduced, warning distinguishes timeout)
7. STRONG_BUY with 1 missing agent -> BUY if confidence drops below 0.75
8. Portfolio: 1 ticker fails -> other tickers still analyzed
9. Portfolio: all tickers fail -> empty PortfolioInsight with HOLD
