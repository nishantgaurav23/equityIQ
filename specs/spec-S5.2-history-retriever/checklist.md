# Checklist -- Spec S5.2: History Retriever

## Phase 1: Setup & Dependencies
- [x] Verify S5.1 (InsightVault) is implemented and tests pass
- [x] Create `memory/history_retriever.py`
- [x] Confirm no new pyproject.toml dependencies needed (uses aiosqlite via InsightVault)

## Phase 2: Tests First (TDD)
- [x] Write test file: `tests/test_history_retriever.py`
- [x] Write failing tests for FR-1 (get_ticker_history)
- [x] Write failing tests for FR-2 (get_signal_trend)
- [x] Write failing tests for FR-3 (get_recent_verdicts)
- [x] Write failing tests for FR-5 (SignalSnapshot model)
- [x] Run `python -m pytest tests/test_history_retriever.py -v` -- expect failures (Red)

## Phase 3: Implementation
- [x] Implement SignalSnapshot Pydantic model
- [x] Implement HistoryRetriever.__init__(vault)
- [x] Implement FR-1: get_ticker_history(ticker, limit, offset)
- [x] Implement FR-2: get_signal_trend(ticker, limit)
- [x] Implement FR-3: get_recent_verdicts(limit, offset)
- [x] Run tests -- expect pass (Green) -- 12/12 passed
- [x] Refactor if needed -- clean, no refactor needed

## Phase 4: Integration
- [x] Add `memory/history_retriever.py` to memory module (update __init__ if needed)
- [x] Run `ruff check memory/history_retriever.py tests/test_history_retriever.py` -- all checks passed
- [x] Run full test suite: `python -m pytest tests/ -v --tb=short` -- 382/382 passed

## Phase 5: Verification
- [x] All tangible outcomes checked
- [x] No hardcoded secrets
- [x] Logging includes relevant context (ticker, limit)
- [x] Update roadmap.md status: spec-written -> done
