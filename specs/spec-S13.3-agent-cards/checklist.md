# Checklist -- Spec S13.3: Agent Signal Cards

## Phase 1: Setup & Dependencies
- [x] Verify S13.2 (analysis page) is implemented and tests pass
- [x] Confirm existing components: `AnalystSignals.tsx`, `SignalBadge.tsx`
- [x] Confirm `frontend/types/api.ts` has current FinalVerdict type

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_agent_cards.py`
- [x] Write failing tests for agent metadata, types, components, integration
- [x] Run tests -- expect failures (Red)

## Phase 3: Implementation
- [x] FR-1: Create `frontend/lib/agents.ts` with 7-agent metadata registry
- [x] FR-2: Add `AgentDetail` type and extend `FinalVerdict` in `types/api.ts`
- [x] FR-3: Create `frontend/app/components/AgentCard.tsx`
- [x] FR-4: Create `frontend/app/components/AgentCardGrid.tsx`
- [x] FR-5: Implement color-coded signal styling in AgentCard
- [x] FR-6: Update `page.tsx` to use AgentCardGrid instead of AnalystSignals
- [x] Run tests -- expect pass (Green)
- [x] Refactor if needed

## Phase 4: Integration
- [x] Verify TypeScript compiles: `npx tsc --noEmit`
- [x] Run full test suite

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] Update roadmap.md status: spec-written -> done
