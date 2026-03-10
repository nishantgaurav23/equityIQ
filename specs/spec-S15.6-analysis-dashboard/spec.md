# S15.6 -- Analysis Dashboard Redesign

## Feature
Complete main page redesign with orchestrator, rich agent cards, results panel

## Location
- `frontend/app/page.tsx`
- `frontend/app/components/`

## Depends On
- S15.2 (rich response)
- S15.4 (design system)
- S15.5 (autocomplete)

## Description
Redesign the main analysis page with:

1. **Hero section** with title, subtitle, tech badges (A2A Protocol, Gemini, 7 Agents)
2. **Ticker autocomplete search** (from S15.5)
3. **Orchestrator card** showing: analysis progress, protocol info (A2A v0.3.0, JSONRPC),
   active agents count, LLM model, status messages
4. **Agent cards grid** (3x2) with: agent icon, name, completion status, data source badge,
   numeric signal value, confidence %, brief analysis summary
5. **Results panel**: large signal badge (BUY/HOLD/SELL), metrics row (confidence, weighted
   signal, risk level, execution time), analysis rationale, key drivers
6. All with Framer Motion stagger animations

## Components to Create/Update
- `OrchestratorCard.tsx`
- `AgentCard.tsx` (redesign)
- `ResultsPanel.tsx`
- `MetricsRow.tsx`
- `SignalBadge.tsx` (redesign)

## Acceptance Criteria
1. Dark glassmorphism layout matching design system
2. Orchestrator card with protocol metadata
3. Agent cards show real data from analyst_details
4. Results panel with comprehensive metrics
5. Framer Motion animations on all cards
6. Responsive: 1 col mobile, 2 col tablet, 3 col desktop
7. Loading states with animated progress
