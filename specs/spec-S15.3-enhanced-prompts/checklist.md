# S15.3 -- Enhanced Agent Prompts -- Checklist

## Status: pending

## TDD Checklist

- [ ] **Write tests** (`tests/test_enhanced_prompts.py`)
  - [ ] Test PERSONAS dict has all 7 agent keys
  - [ ] Test each prompt has minimum length (>= 500 chars)
  - [ ] Test each prompt mentions signal scale (-1.0 to +1.0 or BUY/HOLD/SELL)
  - [ ] Test each prompt mentions confidence scoring
  - [ ] Test each prompt requires JSON output format
  - [ ] Test each prompt includes decision logic / criteria
  - [ ] Test each prompt includes data source attribution
- [ ] **Implement prompts** (`config/analyst_personas.py`)
  - [ ] Rewrite ValuationScout prompt with signal logic + metrics
  - [ ] Rewrite MomentumTracker prompt with signal logic + metrics
  - [ ] Rewrite PulseMonitor prompt with signal logic + metrics
  - [ ] Rewrite EconomyWatcher prompt with signal logic + metrics
  - [ ] Rewrite ComplianceChecker prompt with signal logic + metrics
  - [ ] Rewrite SignalSynthesizer prompt with fusion logic
  - [ ] Rewrite RiskGuardian prompt with risk logic + metrics
  - [ ] Each prompt: directional signal guidelines
  - [ ] Each prompt: confidence scoring criteria
  - [ ] Each prompt: required key metrics
  - [ ] Each prompt: decision logic table
  - [ ] Each prompt: data source attribution
  - [ ] Each prompt: structured JSON output requirement
- [ ] **Verify**
  - [ ] All tests pass: `python -m pytest tests/test_enhanced_prompts.py -v`
  - [ ] Existing agent tests still pass
  - [ ] Ruff clean: `ruff check config/analyst_personas.py`
