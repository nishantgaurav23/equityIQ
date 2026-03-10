# Checklist S10.2 -- Graceful Degradation

## Implementation

- [x] FR-1: Post-synthesis confidence reduction (0.20 per missing directional agent)
- [x] FR-1: Clamp confidence to [0.0, 1.0] after reduction
- [x] FR-2: Add warning entries to key_drivers for failed/timed-out agents
- [x] FR-2: Distinguish timeout vs exception in warning messages
- [x] FR-3: Partial results returned even with some agents missing
- [x] FR-3: RiskGuardian failure does NOT reduce directional confidence
- [x] FR-4: Timeout handling treats timeout same as failure for confidence
- [x] FR-5: Portfolio graceful degradation (skip failed tickers)
- [x] FR-6: STRONG_BUY/STRONG_SELL downgrade when confidence < 0.75

## Tests

- [x] test_no_degradation_all_agents_succeed
- [x] test_one_agent_fails_confidence_reduced
- [x] test_two_agents_fail_confidence_reduced
- [x] test_all_directional_agents_fail_hold_zero
- [x] test_risk_guardian_failure_no_confidence_penalty
- [x] test_timeout_reduces_confidence_with_warning
- [x] test_strong_buy_downgrade_on_low_confidence
- [x] test_strong_sell_downgrade_on_low_confidence
- [x] test_warning_in_key_drivers_on_failure
- [x] test_warning_distinguishes_timeout_from_error
- [x] test_portfolio_partial_ticker_failure
- [x] test_portfolio_all_tickers_fail

## Verification

- [x] All tests pass (44 market_conductor tests, 694 total)
- [x] Ruff lint clean
- [x] Existing tests still pass (no regressions)
