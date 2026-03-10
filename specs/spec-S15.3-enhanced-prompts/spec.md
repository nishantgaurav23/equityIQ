# S15.3 -- Enhanced Agent Prompts

## Feature
Improved agent system prompts with clearer signal guidelines.

## Location
- `config/analyst_personas.py`

## Depends On
- S2.3 (agent personas)

## Description
Rewrite all 7 agent system prompts with:

1. **Clear directional signal guidelines** -- -1.0 to +1.0 scale explanation mapped to BUY/HOLD/SELL
2. **Explicit confidence scoring criteria** -- what constitutes 80% vs 50% vs 30%
3. **Key metrics each agent MUST include** in response
4. **Decision logic tables** -- what data patterns map to what signals
5. **Data source attribution requirement**
6. **Professional, concise analysis style**

Prompts should be better than reference project but not copied.

## Acceptance Criteria

1. All 7 `PERSONAS` entries updated
2. Each prompt includes signal decision logic
3. Each prompt requires structured JSON output
4. Tests verify `PERSONAS` dict has all 7 entries and minimum prompt length
5. Existing agent tests still pass
