# Checklist -- Spec S3.5: Technical Engine

## Phase 1: Setup & Dependencies
- [x] Verify no spec dependencies (S3.5 has none)
- [x] Create target file: `tools/technical_engine.py`
- [x] Ensure numpy is in pyproject.toml dependencies

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_technical_engine.py`
- [x] Write failing tests for calc_rsi (basic, all-up, all-down, insufficient, empty)
- [x] Write failing tests for calc_macd (basic, insufficient, empty, keys)
- [x] Write failing tests for calc_sma (basic, partial, empty)
- [x] Write failing tests for calc_volatility (basic, constant, insufficient, empty)
- [x] Write test for no external API dependencies
- [x] Run `make local-test` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement _calc_ema() helper
- [x] Implement calc_rsi() -- pass RSI tests
- [x] Implement calc_macd() -- pass MACD tests
- [x] Implement calc_sma() -- pass SMA tests
- [x] Implement calc_volatility() -- pass volatility tests
- [x] Run tests -- expect all pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Ensure `tools/__init__.py` exports public functions (if applicable)
- [x] Run `make local-lint`
- [x] Run full test suite: `make local-test`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets (N/A for this module)
- [x] No external API calls in module
- [x] Update roadmap.md status: spec-written -> done
