# S15.5 -- Ticker Autocomplete Checklist

## TDD Checklist

- [ ] **Red**: Write tests for debounced search triggering after 300ms
- [ ] **Red**: Write tests for dropdown rendering ticker + company name
- [ ] **Red**: Write tests for keyboard navigation (ArrowUp, ArrowDown, Enter)
- [ ] **Red**: Write tests for click-to-select from dropdown
- [ ] **Red**: Write tests for popular stocks quick-select buttons
- [ ] **Red**: Write tests for loading spinner state
- [ ] **Red**: Write tests for glassmorphism dropdown styling classes
- [ ] **Green**: Create TickerSearch.tsx with debounced input
- [ ] **Green**: Implement /api/v1/search query in frontend/lib/api.ts
- [ ] **Green**: Render dropdown with ticker + company name matches
- [ ] **Green**: Add keyboard navigation (up/down arrows + Enter)
- [ ] **Green**: Add click handler for dropdown items
- [ ] **Green**: Add popular stocks buttons (AAPL, GOOGL, MSFT, NVDA, TSLA, AMZN)
- [ ] **Green**: Add loading spinner while fetching
- [ ] **Green**: Apply glassmorphism styling to dropdown
- [ ] **Refactor**: Verify all tests pass
- [ ] **Refactor**: Run ruff lint (line-length: 100)
- [ ] **Refactor**: Update checklist -- all boxes checked
