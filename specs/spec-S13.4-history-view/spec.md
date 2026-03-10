# Spec S13.4 -- History View

## Overview

Analysis history page for the Next.js frontend. Shows past analyses for a given ticker, including a signal trend chart that visualizes how the signal evolved over time. Supports filtering by date range. Consumes `GET /api/v1/history/{ticker}` and `GET /api/v1/history/{ticker}/trend` backend endpoints (S9.3).

## Dependencies

| Spec | What It Provides |
|------|-----------------|
| S13.1 | Next.js scaffold with App Router, TypeScript, Tailwind, API client (`lib/api.ts`), types (`types/api.ts`) |
| S9.3 | `GET /api/v1/history/{ticker}` (past verdicts), `GET /api/v1/history/{ticker}/trend` (signal snapshots) |

## Target Location

- `frontend/app/history/page.tsx` -- History page (ticker input + results)
- `frontend/app/history/components/HistoryTable.tsx` -- Table of past verdicts
- `frontend/app/history/components/SignalTrendChart.tsx` -- Signal trend visualization
- `frontend/app/history/components/DateRangeFilter.tsx` -- Date range filter controls
- `frontend/lib/api.ts` -- Add `getTickerHistory()` and `getSignalTrend()` API functions
- `frontend/types/api.ts` -- Add `SignalSnapshot` type
- `tests/test_history_view.py` -- Python structural/integration tests

---

## Functional Requirements

### FR-1: SignalSnapshot Type Definition
- **What**: Add `SignalSnapshot` interface to `types/api.ts` matching backend model
- **Inputs**: None
- **Outputs**: `SignalSnapshot` type with `session_id`, `ticker`, `final_signal`, `overall_confidence`, `created_at` fields
- **Edge cases**: `created_at` is ISO 8601 string

### FR-2: API Client Functions
- **What**: Add `getTickerHistory()` and `getSignalTrend()` to `lib/api.ts`
- **Inputs**: `ticker: string`, optional `limit?: number`, optional `offset?: number` (history only)
- **Outputs**: `getTickerHistory(ticker, limit?, offset?): Promise<FinalVerdict[]>`, `getSignalTrend(ticker, limit?): Promise<SignalSnapshot[]>`
- **Edge cases**: URL-encode ticker, default limit/offset handled by backend

### FR-3: History Page
- **What**: Page at `/history` with ticker input field, search button, and results area
- **Inputs**: User types a ticker symbol and clicks search (or presses Enter)
- **Outputs**: Renders history table and signal trend chart for the searched ticker
- **Edge cases**: Empty ticker shows validation message, no results shows "No history found" message, loading state while fetching, API errors displayed gracefully

### FR-4: History Table Component
- **What**: Table displaying past `FinalVerdict` records for a ticker
- **Inputs**: `FinalVerdict[]` array
- **Outputs**: Table with columns: Date, Signal (color-coded badge), Confidence (%), Key Drivers, Session ID (truncated). Sorted newest first. Paginated (20 per page).
- **Edge cases**: Empty array shows "No analyses found" message, signal badges color-coded (green=BUY/STRONG_BUY, red=SELL/STRONG_SELL, yellow=HOLD)

### FR-5: Signal Trend Chart Component
- **What**: Visual chart showing signal evolution over time using colored markers or a line chart
- **Inputs**: `SignalSnapshot[]` array (chronological, oldest first)
- **Outputs**: Chart with X-axis = date, Y-axis = signal level (STRONG_SELL=-2, SELL=-1, HOLD=0, BUY=1, STRONG_BUY=2), dot size or opacity proportional to confidence. Uses CSS/SVG (no heavy chart library required, but recharts acceptable if already available).
- **Edge cases**: Single data point shown as dot, empty data shows placeholder message, responsive width

### FR-6: Date Range Filter
- **What**: Filter controls to narrow history results by date range
- **Inputs**: Start date and end date inputs (HTML date pickers)
- **Outputs**: Filters the displayed verdicts and trend data client-side. "Clear" button to reset filters.
- **Edge cases**: Start date after end date shows validation error, no results in range shows message

### FR-7: Navigation Link
- **What**: Add History link to the layout header navigation
- **Inputs**: None
- **Outputs**: Link in header nav pointing to `/history`
- **Edge cases**: Active link highlighted when on history page

---

## Tangible Outcomes

- [ ] **Outcome 1**: `frontend/types/api.ts` exports `SignalSnapshot` interface with correct fields
- [ ] **Outcome 2**: `frontend/lib/api.ts` exports `getTickerHistory()` and `getSignalTrend()` functions
- [ ] **Outcome 3**: `/history` page renders with ticker input, search button, and results area
- [ ] **Outcome 4**: History table displays FinalVerdict records with color-coded signal badges
- [ ] **Outcome 5**: Signal trend chart visualizes signal evolution over time
- [ ] **Outcome 6**: Date range filter narrows displayed results
- [ ] **Outcome 7**: Header navigation includes link to `/history`
- [ ] **Outcome 8**: `npm run build` in `frontend/` succeeds without errors
- [ ] **Outcome 9**: All Python structural tests pass

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_history_page_exists**: Verify `frontend/app/history/page.tsx` exists
2. **test_history_table_component_exists**: Verify `frontend/app/history/components/HistoryTable.tsx` exists
3. **test_signal_trend_chart_exists**: Verify `frontend/app/history/components/SignalTrendChart.tsx` exists
4. **test_date_range_filter_exists**: Verify `frontend/app/history/components/DateRangeFilter.tsx` exists
5. **test_signal_snapshot_type_defined**: Verify `types/api.ts` contains `SignalSnapshot` interface
6. **test_api_client_history_functions**: Verify `lib/api.ts` exports `getTickerHistory` and `getSignalTrend`
7. **test_history_page_has_ticker_input**: Verify page.tsx contains ticker input element
8. **test_history_table_has_signal_badges**: Verify HistoryTable renders signal-based color classes
9. **test_trend_chart_has_signal_mapping**: Verify SignalTrendChart maps signals to numeric values
10. **test_layout_has_history_link**: Verify layout.tsx contains link to `/history`
11. **test_next_build_succeeds**: Run `npm run build` in frontend/ and verify exit code 0

### Mocking Strategy
- Python tests verify file existence and content patterns (no React rendering)
- File content checks via regex for key patterns (interface names, function exports, JSX elements)

### Coverage Expectation
- All files verified to exist
- Key content patterns verified (types, exports, UI elements)
- Build succeeds without errors

---

## References
- roadmap.md -- S13.4 row
- specs/spec-S13.1-nextjs-scaffold/spec.md -- scaffold structure
- specs/spec-S9.3-history-endpoints/spec.md -- backend history endpoints
- frontend/types/api.ts -- existing type definitions
- frontend/lib/api.ts -- existing API client
