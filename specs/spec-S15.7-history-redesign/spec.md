# S15.7 -- History Page Redesign

## Feature
Enhanced history page with stats, filters, detail modal

## Location
- `frontend/app/history/page.tsx`
- `frontend/app/history/components/`

## Depends On
- S15.4 (design system)
- S9.3 (history endpoints)

## Description
Redesign history page with:

1. **Stats bar**: Total analyses, BUY count, SELL count, HOLD count, Average Confidence
2. **Signal filter tabs**: All | BUY | SELL | HOLD
3. **History rows** (glassmorphism cards): Ticker, signal badge, time ago, confidence %,
   risk level, execution time
4. **Click row** to open detail modal showing: full verdict with metrics, per-agent
   breakdown, analysis rationale, data flow info
5. **Clear All button** (with confirmation)

## Components to Create/Update
- `StatsBar.tsx`
- `FilterTabs.tsx`
- `HistoryRow.tsx`
- `AnalysisDetailModal.tsx`

## Acceptance Criteria
1. Stats bar shows aggregated counts
2. Filter tabs work correctly
3. History rows with rich data
4. Detail modal with full breakdown
5. Responsive layout
6. Framer Motion animations
