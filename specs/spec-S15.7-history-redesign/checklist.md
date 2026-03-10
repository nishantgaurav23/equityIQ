# S15.7 -- History Page Redesign Checklist

## TDD Checklist

- [ ] **Red**: Write tests for StatsBar (total, BUY/SELL/HOLD counts, avg confidence)
- [ ] **Red**: Write tests for FilterTabs (All, BUY, SELL, HOLD filtering)
- [ ] **Red**: Write tests for HistoryRow (ticker, signal badge, time ago, confidence, risk)
- [ ] **Red**: Write tests for AnalysisDetailModal (verdict, agents, rationale, data flow)
- [ ] **Red**: Write tests for Clear All with confirmation dialog
- [ ] **Red**: Write tests for responsive layout
- [ ] **Green**: Create StatsBar.tsx with aggregated counts
- [ ] **Green**: Create FilterTabs.tsx with All/BUY/SELL/HOLD tabs
- [ ] **Green**: Create HistoryRow.tsx with glassmorphism card styling
- [ ] **Green**: Create AnalysisDetailModal.tsx with full breakdown view
- [ ] **Green**: Add Clear All button with confirmation dialog
- [ ] **Green**: Apply responsive layout
- [ ] **Green**: Add Framer Motion animations
- [ ] **Refactor**: Verify all tests pass
- [ ] **Refactor**: Run ruff lint (line-length: 100)
- [ ] **Refactor**: Update checklist -- all boxes checked
