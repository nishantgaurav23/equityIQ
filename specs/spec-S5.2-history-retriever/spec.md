# Spec S5.2 -- History Retriever

## Overview
Query past analyses stored in InsightVault. Provides `get_ticker_history()`, `get_signal_trend()`, and `get_recent_verdicts()` functions that return structured data suitable for API endpoints (S9.3) and backtesting (S14.3).

## Dependencies
- **S5.1** -- InsightVault (SQLite session storage)

## Target Location
- `memory/history_retriever.py`

---

## Functional Requirements

### FR-1: get_ticker_history(ticker, limit, offset)
- **What**: Retrieve all past verdicts for a given ticker, ordered by most recent first
- **Inputs**: `ticker: str` (required), `limit: int = 50` (max 200), `offset: int = 0`
- **Outputs**: `list[FinalVerdict]` -- deserialized verdict objects
- **Edge cases**: Unknown ticker returns empty list. Invalid ticker (empty string) returns empty list. Limit clamped to [1, 200].

### FR-2: get_signal_trend(ticker, limit)
- **What**: Return a time-ordered list of signal/confidence pairs for a ticker, showing how the signal evolved over time. Useful for trend visualization.
- **Inputs**: `ticker: str` (required), `limit: int = 20` (max 100)
- **Outputs**: `list[SignalSnapshot]` where `SignalSnapshot` is a Pydantic model with fields: `session_id: str`, `final_signal: str`, `overall_confidence: float`, `created_at: str`. Ordered chronologically (oldest first).
- **Edge cases**: Unknown ticker returns empty list. Fewer results than limit is normal.

### FR-3: get_recent_verdicts(limit, offset)
- **What**: Retrieve the most recent verdicts across all tickers
- **Inputs**: `limit: int = 20` (max 200), `offset: int = 0`
- **Outputs**: `list[FinalVerdict]` -- ordered by created_at DESC
- **Edge cases**: Empty database returns empty list.

### FR-4: HistoryRetriever class design
- **What**: Encapsulate all history query functions in a `HistoryRetriever` class that receives an `InsightVault` instance via constructor injection
- **Constructor**: `__init__(self, vault: InsightVault)`
- **Rationale**: Dependency injection keeps it testable and decoupled from vault lifecycle

### FR-5: SignalSnapshot Pydantic model
- **What**: Define a lightweight data model for signal trend entries in `memory/history_retriever.py`
- **Fields**: `session_id: str`, `ticker: str`, `final_signal: str`, `overall_confidence: float`, `created_at: str`
- **Validation**: `overall_confidence` clamped to [0.0, 1.0]

---

## Tangible Outcomes

- [ ] **Outcome 1**: `memory/history_retriever.py` exists with `HistoryRetriever` class and `SignalSnapshot` model
- [ ] **Outcome 2**: `get_ticker_history("AAPL")` returns list of FinalVerdict objects for AAPL, ordered newest first
- [ ] **Outcome 3**: `get_signal_trend("AAPL")` returns list of SignalSnapshot ordered oldest first (chronological)
- [ ] **Outcome 4**: `get_recent_verdicts()` returns most recent verdicts across all tickers
- [ ] **Outcome 5**: Empty/unknown ticker queries return empty lists (no exceptions)
- [ ] **Outcome 6**: Limit clamping enforced (get_ticker_history max 200, get_signal_trend max 100, get_recent_verdicts max 200)
- [ ] **Outcome 7**: All tests pass: `python -m pytest tests/test_history_retriever.py -v`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_get_ticker_history_returns_verdicts**: Store 3 AAPL verdicts, retrieve, assert count and order
2. **test_get_ticker_history_empty_ticker**: Pass empty string, expect empty list
3. **test_get_ticker_history_unknown_ticker**: Query ticker with no data, expect empty list
4. **test_get_ticker_history_limit_clamping**: Pass limit=500, verify clamped to 200
5. **test_get_ticker_history_offset**: Store 5 verdicts, use offset=2 limit=2, verify correct slice
6. **test_get_signal_trend_chronological_order**: Store verdicts at different times, verify oldest-first order
7. **test_get_signal_trend_returns_snapshots**: Verify returned objects are SignalSnapshot with correct fields
8. **test_get_signal_trend_limit_clamping**: Pass limit=500, verify clamped to 100
9. **test_get_signal_trend_empty**: Query unknown ticker, expect empty list
10. **test_get_recent_verdicts**: Store verdicts for multiple tickers, retrieve recent, verify mixed tickers
11. **test_get_recent_verdicts_limit_and_offset**: Verify pagination works
12. **test_signal_snapshot_confidence_clamping**: Verify confidence clamped to [0, 1]

### Mocking Strategy
- No external API mocking needed -- uses InsightVault with in-memory/temp SQLite
- Use `tmp_path` pytest fixture for temporary database files
- Create a shared fixture that provides an initialized InsightVault + HistoryRetriever

### Coverage Expectation
- All public methods have at least one happy-path and one edge-case test

---

## References
- roadmap.md -- S5.2 row
- memory/insight_vault.py -- S5.1 implementation (data source)
- config/data_contracts.py -- FinalVerdict schema
- design.md -- memory layer architecture
