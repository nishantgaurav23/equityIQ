# S15.6 -- Analysis Dashboard Redesign Checklist

## TDD Checklist

- [ ] **Red**: Write tests for hero section rendering (title, subtitle, tech badges)
- [ ] **Red**: Write tests for OrchestratorCard (protocol info, agent count, status)
- [ ] **Red**: Write tests for AgentCard (icon, name, signal, confidence, summary)
- [ ] **Red**: Write tests for ResultsPanel (signal badge, metrics, rationale, drivers)
- [ ] **Red**: Write tests for MetricsRow (confidence, weighted signal, risk, time)
- [ ] **Red**: Write tests for SignalBadge (BUY/HOLD/SELL color variants)
- [ ] **Red**: Write tests for responsive layout breakpoints
- [ ] **Red**: Write tests for loading states with animated progress
- [ ] **Green**: Create hero section with title, subtitle, tech badges
- [ ] **Green**: Integrate TickerSearch autocomplete component
- [ ] **Green**: Create OrchestratorCard.tsx with protocol metadata
- [ ] **Green**: Redesign AgentCard.tsx with icon, signal, confidence, summary
- [ ] **Green**: Create ResultsPanel.tsx with signal badge and metrics
- [ ] **Green**: Create MetricsRow.tsx for confidence, weighted signal, risk, time
- [ ] **Green**: Redesign SignalBadge.tsx with BUY/HOLD/SELL color variants
- [ ] **Green**: Add Framer Motion stagger animations on all cards
- [ ] **Green**: Implement responsive grid (1/2/3 col)
- [ ] **Green**: Add loading states with animated progress
- [ ] **Refactor**: Verify all tests pass
- [ ] **Refactor**: Run ruff lint (line-length: 100)
- [ ] **Refactor**: Update checklist -- all boxes checked
