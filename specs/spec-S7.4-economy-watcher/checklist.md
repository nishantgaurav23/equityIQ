# Checklist -- Spec S7.4: EconomyWatcher Agent

## Phase 1: Setup & Dependencies
- [x] Verify S6.1 (agent base) is implemented and tests pass
- [x] Verify S3.2 (FRED connector) is implemented and tests pass
- [x] Create `agents/economy_watcher.py`
- [x] Create `tests/test_economy_watcher.py`

## Phase 2: Tests First (TDD)
- [x] T1: Test instantiation (agent_name, output_schema, tools)
- [x] T2: Test `get_macro_indicators_tool()` calls FredConnector correctly
- [x] T2: Test `get_macro_indicators_tool()` returns `{}` on error
- [x] T3: Test `analyze("AAPL")` with mocked LLM returns valid EconomyReport
- [x] T4: Test `analyze()` fallback on exception (HOLD/0.0)
- [x] T5: Test `get_agent_card()` returns correct card
- [x] T6: Test `create_economy_watcher()` factory and module-level instance
- [x] Run `pytest tests/test_economy_watcher.py -v` -- 17/17 passed

## Phase 3: Implementation
- [x] Implement `get_macro_indicators_tool()` with try/except
- [x] Implement `EconomyWatcher` class extending `BaseAnalystAgent`
- [x] Implement `create_economy_watcher()` factory
- [x] Create module-level `economy_watcher` instance
- [x] Run tests -- 17/17 passed (Green)
- [x] N/A -- no refactoring needed

## Phase 4: Integration
- [x] Run `ruff check agents/economy_watcher.py` -- all checks passed
- [x] Run `ruff format agents/economy_watcher.py` -- already formatted
- [x] Run full test suite: 520/520 passed

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] Logging includes warnings on failures
- [x] Update roadmap.md status: spec-written -> done
