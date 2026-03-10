# Checklist -- Spec S13.2: Stock Analysis Page

## Phase 1: Setup & Dependencies
- [x] Verify S13.1 (Next.js scaffold) is implemented and tests pass
- [x] Verify S9.1 (analyze endpoint) is implemented and tests pass
- [x] Verify `frontend/lib/api.ts` exports `analyzeStock()`
- [x] Verify `frontend/types/api.ts` defines `FinalVerdict` and `FinalSignal`

## Phase 2: Tests First (TDD)
- [x] Add analysis page tests to `tests/test_nextjs_scaffold.py`
- [x] Write test_page_has_ticker_input
- [x] Write test_page_has_submit_button
- [x] Write test_page_imports_analyze_stock
- [x] Write test_signal_badge_component_exists
- [x] Write test_confidence_meter_component_exists
- [x] Write test_key_drivers_component_exists
- [x] Write test_analyst_signals_component_exists
- [x] Write test_page_has_error_handling
- [x] Write test_page_has_loading_state
- [x] Write test_signal_badge_colors
- [x] Write test_typescript_compiles
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement SignalBadge component (`frontend/components/SignalBadge.tsx`)
- [x] Implement ConfidenceMeter component (`frontend/components/ConfidenceMeter.tsx`)
- [x] Implement KeyDrivers component (`frontend/components/KeyDrivers.tsx`)
- [x] Implement AnalystSignals component (`frontend/components/AnalystSignals.tsx`)
- [x] Update page.tsx with ticker input form
- [x] Add loading state to page.tsx
- [x] Add error handling to page.tsx
- [x] Add result display layout to page.tsx
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify page uses `analyzeStock()` from `lib/api.ts`
- [x] Verify all components properly import types from `types/api.ts`
- [x] Run `npx tsc --noEmit` in frontend/ -- no type errors
- [x] Run full test suite: `python -m pytest tests/test_nextjs_scaffold.py -v`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded API URLs (uses config)
- [x] Loading state prevents double submission
- [x] Error messages are user-friendly
- [x] Signal badge colors match all 5 signal types
- [x] Update roadmap.md status: spec-written -> done
