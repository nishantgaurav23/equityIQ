# S15.5 -- Ticker Autocomplete Component

## Feature
Smart ticker search with autocomplete dropdown

## Location
- `frontend/components/TickerSearch.tsx`
- `frontend/lib/api.ts`

## Depends On
- S15.1 (ticker search API)
- S15.4 (design system)

## Description
Replace simple text input with a search component that queries /api/v1/search as user
types (debounced 300ms). Shows dropdown with matching companies (ticker + name). User
can click a result or press Enter. Supports keyboard navigation (up/down arrows). Shows
loading spinner while searching. Glassmorphism dropdown styling. Popular stocks
quick-select buttons below input.

## Acceptance Criteria
1. Debounced search (300ms) on keystroke
2. Dropdown shows ticker + company name matches
3. Keyboard navigation (arrows + Enter)
4. Click to select from dropdown
5. Popular stocks buttons (AAPL, GOOGL, MSFT, NVDA, TSLA, AMZN)
6. Loading state with spinner
7. Glassmorphism styled dropdown
