# Spec S13.3 -- Agent Signal Cards

## Overview
Individual card components for each of the 7 specialist agents, displaying signal, confidence, key metrics, and reasoning. Cards are color-coded by signal (BUY=green, HOLD=yellow, SELL=red). Replaces the minimal `AnalystSignals` grid from S13.2 with rich, expandable agent cards showing per-agent detail.

## Dependencies
- S13.2 (Analysis page -- provides FinalVerdict display, existing AnalystSignals component)

## Target Location
- `frontend/app/components/AgentCard.tsx` -- individual agent card component
- `frontend/app/components/AgentCardGrid.tsx` -- grid layout for all agent cards
- `frontend/lib/agents.ts` -- agent metadata (name, role, description, icon)
- `frontend/types/api.ts` -- extend with `AgentDetail` type for per-agent data
- `frontend/app/page.tsx` -- replace AnalystSignals with AgentCardGrid

---

## Functional Requirements

### FR-1: Agent Metadata Registry
- **What**: A `frontend/lib/agents.ts` module exporting metadata for each of the 7 agents: display name, role description, icon emoji, and category.
- **Inputs**: Agent name string (e.g., "ValuationScout")
- **Outputs**: `AgentMeta` object with `displayName`, `role`, `icon`, `category`
- **Edge cases**: Unknown agent name returns a default/fallback metadata

### FR-2: AgentDetail Type
- **What**: Extend `frontend/types/api.ts` with an `AgentDetail` interface containing agent-level signal, confidence, and reasoning. Extend `FinalVerdict` to optionally include `analyst_details: Record<string, AgentDetail>` alongside existing `analyst_signals`.
- **Inputs**: N/A (type definition)
- **Outputs**: `AgentDetail` type: `{ signal: Signal; confidence: number; reasoning: string; key_metrics: Record<string, string | number | boolean | null> }`
- **Edge cases**: `analyst_details` is optional on FinalVerdict for backward compatibility

### FR-3: AgentCard Component
- **What**: A card component that displays one agent's analysis result. Shows: agent icon + name, role description, signal badge (color-coded), confidence bar, key metrics list, reasoning text (truncated with expand toggle).
- **Inputs**: `agentName: string`, `signal: string`, `detail?: AgentDetail`
- **Outputs**: Styled card with color-coded border (green/yellow/red based on signal), agent metadata, and optional detail section
- **Edge cases**: When no `detail` is provided, shows only agent name and signal (graceful fallback). Reasoning truncated to 120 chars with "Show more" toggle.

### FR-4: AgentCardGrid Component
- **What**: A responsive grid layout that renders `AgentCard` for each agent in `analyst_signals`. Replaces the existing `AnalystSignals` component usage in `page.tsx`.
- **Inputs**: `signals: Record<string, string>`, `details?: Record<string, AgentDetail>`
- **Outputs**: Responsive grid (1 col mobile, 2 col tablet, 3 col desktop) of AgentCards
- **Edge cases**: Empty signals shows "No agent signals available" message. Grid handles 1-7 agents gracefully.

### FR-5: Color-Coded Signal Styling
- **What**: Cards have color-coded left border and signal badge: BUY/STRONG_BUY = green, HOLD = yellow/amber, SELL/STRONG_SELL = red. Signal text is bold and colored.
- **Inputs**: Signal string
- **Outputs**: Appropriate Tailwind CSS classes for border, badge background, text color
- **Edge cases**: Unknown signal defaults to gray styling

### FR-6: Integration with Analysis Page
- **What**: Replace the `<AnalystSignals>` usage in `page.tsx` with `<AgentCardGrid>`. Pass `analyst_signals` and optionally `analyst_details` from the FinalVerdict.
- **Inputs**: FinalVerdict from analysis result
- **Outputs**: Agent cards displayed in the result section
- **Edge cases**: Works with existing FinalVerdict shape (no `analyst_details` field yet)

---

## Tangible Outcomes

- [ ] **Outcome 1**: `frontend/lib/agents.ts` exists with metadata for all 7 agents
- [ ] **Outcome 2**: `frontend/types/api.ts` contains `AgentDetail` interface
- [ ] **Outcome 3**: `frontend/app/components/AgentCard.tsx` exists and renders a single agent card
- [ ] **Outcome 4**: `frontend/app/components/AgentCardGrid.tsx` exists and renders a responsive grid
- [ ] **Outcome 5**: Cards are color-coded: green (BUY), yellow (HOLD), red (SELL)
- [ ] **Outcome 6**: `page.tsx` uses `AgentCardGrid` instead of `AnalystSignals`
- [ ] **Outcome 7**: Cards show agent icon, name, role, signal, and optional confidence/reasoning
- [ ] **Outcome 8**: All tests pass
- [ ] **Outcome 9**: `npx tsc --noEmit` passes with no type errors

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_agents_metadata_file_exists**: `frontend/lib/agents.ts` exists
2. **test_agents_metadata_has_all_agents**: Contains metadata for all 7 agents
3. **test_agent_detail_type_exists**: `frontend/types/api.ts` contains `AgentDetail` interface
4. **test_final_verdict_has_analyst_details**: `FinalVerdict` type includes optional `analyst_details`
5. **test_agent_card_component_exists**: `frontend/app/components/AgentCard.tsx` exists
6. **test_agent_card_has_signal_coloring**: AgentCard contains signal-to-color mapping
7. **test_agent_card_has_confidence_display**: AgentCard renders confidence information
8. **test_agent_card_grid_component_exists**: `frontend/app/components/AgentCardGrid.tsx` exists
9. **test_agent_card_grid_responsive**: AgentCardGrid has responsive grid classes
10. **test_agent_card_grid_empty_state**: AgentCardGrid handles empty signals
11. **test_page_uses_agent_card_grid**: `page.tsx` imports and uses `AgentCardGrid`
12. **test_typescript_compiles**: `npx tsc --noEmit` passes

### Mocking Strategy
- Tests are structural (file existence, content inspection) using Python pytest
- TypeScript compilation validates type correctness
- No runtime React testing required -- structural validation sufficient

### Coverage Expectation
- All component files verified to exist with correct content
- TypeScript compilation passes
- Page integration validated

---

## References
- roadmap.md, design.md
- S13.2 spec (Analysis page -- existing AnalystSignals component)
- Backend data contracts: `config/data_contracts.py`
- Frontend types: `frontend/types/api.ts`
- Agent roster: CLAUDE.md (7 agents with ports and responsibilities)
