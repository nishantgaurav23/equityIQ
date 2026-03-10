# Checklist -- Spec S13.4: History View

## Phase 1: Setup & Dependencies
- [x] Verify S13.1 (Next.js scaffold) is implemented -- `frontend/` exists with working build
- [x] Verify S9.3 (history endpoints) is implemented -- backend endpoints exist
- [x] Create directory `frontend/app/history/components/`

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_history_view.py`
- [x] Write failing tests for file existence (page, components, types, API functions)
- [x] Write failing tests for content patterns (SignalSnapshot, getTickerHistory, signal badges)
- [x] Run `python -m pytest tests/test_history_view.py -v` -- expect failures (Red)

## Phase 3: Implementation
- [x] FR-1: Add `SignalSnapshot` interface to `frontend/types/api.ts`
- [x] FR-2: Add `getTickerHistory()` and `getSignalTrend()` to `frontend/lib/api.ts`
- [x] FR-3: Create `frontend/app/history/page.tsx` -- history page with ticker input
- [x] FR-4: Create `frontend/app/history/components/HistoryTable.tsx` -- verdict table
- [x] FR-5: Create `frontend/app/history/components/SignalTrendChart.tsx` -- trend chart
- [x] FR-6: Create `frontend/app/history/components/DateRangeFilter.tsx` -- date filter
- [x] FR-7: Add History link to `frontend/app/layout.tsx` header nav
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify `npm run build` succeeds in `frontend/`
- [x] Run full Python test suite: `python -m pytest tests/test_history_view.py -v`

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded API URLs (uses config)
- [x] Signal color-coding consistent (green=BUY, red=SELL, yellow=HOLD)
- [x] Responsive layout works
- [x] Update roadmap.md status: pending -> done (when ready)
