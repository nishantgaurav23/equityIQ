# Spec S13.2 -- Stock Analysis Page

## Overview
Stock analysis page for the Next.js frontend. Provides a ticker input form with submit button and loading state. On submission, calls the `POST /analyze/{ticker}` backend endpoint and displays the FinalVerdict result with a signal badge (color-coded STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL), confidence meter, key drivers list, and analyst signal summary.

## Dependencies
- S13.1 (Next.js scaffold -- app shell, API client, TypeScript types)
- S9.1 (POST /analyze/{ticker} endpoint -- backend API)

## Target Location
- `frontend/app/page.tsx` -- main analysis page (replaces health-check-only page)
- `frontend/components/SignalBadge.tsx` -- color-coded signal badge component
- `frontend/components/ConfidenceMeter.tsx` -- visual confidence display
- `frontend/components/KeyDrivers.tsx` -- key drivers list component
- `frontend/components/AnalystSignals.tsx` -- analyst signal summary cards

---

## Functional Requirements

### FR-1: Ticker Input Form
- **What**: A form with a text input for the stock ticker and a submit button. Input is validated client-side (non-empty, max 10 chars, letters only).
- **Inputs**: User types a ticker string (e.g., "AAPL", "tsla")
- **Outputs**: On submit, triggers analysis API call. Ticker is uppercased before submission.
- **Edge cases**: Empty input shows validation message. Submitting while already loading is disabled. Special characters rejected.

### FR-2: Loading State
- **What**: While the analysis API call is in progress, show a loading indicator. The submit button is disabled and shows a spinner or "Analyzing..." text. A skeleton or progress indicator is shown in the results area.
- **Inputs**: API call in flight
- **Outputs**: Visual loading feedback to the user
- **Edge cases**: Long-running requests (up to 60s timeout). User cannot submit another request while loading.

### FR-3: Signal Badge Display
- **What**: A `SignalBadge` component that renders the `final_signal` as a colored badge.
- **Inputs**: `final_signal: FinalSignal` (STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL)
- **Outputs**: Colored badge -- green for BUY/STRONG_BUY, yellow for HOLD, red for SELL/STRONG_SELL. STRONG variants are darker/bolder.
- **Edge cases**: Component handles all 5 signal values

### FR-4: Confidence Meter
- **What**: A `ConfidenceMeter` component that visually displays the `overall_confidence` value (0.0 to 1.0).
- **Inputs**: `confidence: number` (0.0 to 1.0)
- **Outputs**: A progress bar or meter showing the confidence percentage. Color grades from red (<0.3) to yellow (0.3-0.6) to green (>0.6). Displays percentage text.
- **Edge cases**: Values clamped to [0, 1]. Handles 0 and 1 correctly.

### FR-5: Key Drivers Display
- **What**: A `KeyDrivers` component that renders the `key_drivers` string array as a styled list.
- **Inputs**: `drivers: string[]`
- **Outputs**: Bulleted or numbered list of key drivers
- **Edge cases**: Empty array shows "No key drivers identified"

### FR-6: Analyst Signals Summary
- **What**: An `AnalystSignals` component that displays the `analyst_signals` record as a summary table or card grid showing each agent's signal.
- **Inputs**: `signals: Record<string, string>` (e.g., {"ValuationScout": "BUY", "MomentumTracker": "HOLD"})
- **Outputs**: Grid/table showing agent name and their signal with color coding
- **Edge cases**: Missing agents are omitted. Empty record shows placeholder.

### FR-7: Error Handling
- **What**: API errors (network failures, 400 bad ticker, 500 server errors) are displayed as user-friendly error messages.
- **Inputs**: `ApiError` thrown by the API client
- **Outputs**: Error message with appropriate context (e.g., "Invalid ticker symbol" for 400, "Server error, please try again" for 500)
- **Edge cases**: Network timeout shows specific message. Error can be dismissed to try again.

### FR-8: Result Display Layout
- **What**: After successful analysis, the page shows the complete FinalVerdict in a structured layout: ticker + signal badge at the top, confidence meter, risk summary, key drivers, and analyst signals grid below.
- **Inputs**: `FinalVerdict` response from API
- **Outputs**: Structured layout with all verdict information
- **Edge cases**: Null `price_target` is omitted or shows "N/A"

---

## Tangible Outcomes

- [ ] **Outcome 1**: `frontend/app/page.tsx` contains a ticker input form that submits to the backend
- [ ] **Outcome 2**: Typing a ticker and clicking submit calls `analyzeStock()` from `lib/api.ts`
- [ ] **Outcome 3**: Loading state is shown while analysis is in progress (button disabled, spinner visible)
- [ ] **Outcome 4**: `frontend/components/SignalBadge.tsx` exists and renders color-coded signal badges
- [ ] **Outcome 5**: `frontend/components/ConfidenceMeter.tsx` exists and renders a visual confidence bar
- [ ] **Outcome 6**: `frontend/components/KeyDrivers.tsx` exists and renders key driver list
- [ ] **Outcome 7**: `frontend/components/AnalystSignals.tsx` exists and renders analyst signal grid
- [ ] **Outcome 8**: Error messages are displayed for API failures (400, 500, network errors)
- [ ] **Outcome 9**: All tests in `tests/test_nextjs_scaffold.py::TestAnalysisPage` pass (structural tests)
- [ ] **Outcome 10**: `npx tsc --noEmit` passes with no type errors in `frontend/`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_page_has_ticker_input**: `page.tsx` contains an input element with appropriate attributes
2. **test_page_has_submit_button**: `page.tsx` contains a submit/analyze button
3. **test_page_imports_analyze_stock**: `page.tsx` imports `analyzeStock` from the API client
4. **test_signal_badge_component_exists**: `components/SignalBadge.tsx` exists with signal-to-color mapping
5. **test_confidence_meter_component_exists**: `components/ConfidenceMeter.tsx` exists with confidence display
6. **test_key_drivers_component_exists**: `components/KeyDrivers.tsx` exists
7. **test_analyst_signals_component_exists**: `components/AnalystSignals.tsx` exists
8. **test_page_has_error_handling**: `page.tsx` includes error state handling
9. **test_page_has_loading_state**: `page.tsx` includes loading state handling
10. **test_signal_badge_colors**: SignalBadge maps all 5 signals to appropriate color classes
11. **test_typescript_compiles**: `npx tsc --noEmit` passes with no errors
12. **test_components_use_typescript**: All component files use proper TypeScript typing

### Mocking Strategy
- Tests are primarily structural (file existence, content inspection) using Python pytest
- TypeScript compilation check validates type correctness
- No runtime React testing (Jest/RTL) required -- structural validation sufficient for this spec

### Coverage Expectation
- All component files verified to exist with correct content
- TypeScript compilation passes
- Page structure validated for required elements

---

## References
- roadmap.md, design.md
- S13.1 spec (Next.js scaffold -- API client, types, layout)
- S9.1 spec (POST /analyze/{ticker} endpoint)
- Backend data contracts: `config/data_contracts.py`
- Frontend types: `frontend/types/api.ts`
