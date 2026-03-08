# S5.1 -- InsightVault Checklist

## Setup
- [x] Create `memory/` directory
- [x] Create `memory/__init__.py` with InsightVault export
- [x] Create `memory/insight_vault.py` skeleton

## Implementation
- [x] InsightVault.__init__ -- accept db_path, default from Settings
- [x] InsightVault.initialize -- create dirs + tables (IF NOT EXISTS)
- [x] InsightVault._get_connection -- lazy aiosqlite connection
- [x] InsightVault.store_verdict -- insert FinalVerdict, generate session_id if empty
- [x] InsightVault.get_verdict -- query by session_id, deserialize JSON
- [x] InsightVault.list_verdicts -- query with optional ticker filter, limit/offset, DESC order
- [x] InsightVault.delete_verdict -- delete by session_id, return bool
- [x] InsightVault.close -- close aiosqlite connection
- [x] Error handling -- try/except on all DB operations, log errors

## Tests
- [x] test_store_and_retrieve_verdict -- round-trip test
- [x] test_store_generates_session_id -- empty session_id gets UUID
- [x] test_store_preserves_session_id -- non-empty session_id kept
- [x] test_get_verdict_not_found -- returns None
- [x] test_list_verdicts_all -- returns all stored verdicts
- [x] test_list_verdicts_by_ticker -- filter works
- [x] test_list_verdicts_limit_offset -- pagination works
- [x] test_list_verdicts_limit_cap -- limit capped at 200
- [x] test_delete_verdict -- deletes and returns True
- [x] test_delete_verdict_not_found -- returns False
- [x] test_initialize_creates_tables -- tables exist after init
- [x] test_round_trip_lossless -- FinalVerdict fields preserved exactly
- [x] test_close -- no errors on close

## Quality
- [x] ruff check passes
- [x] ruff format passes
- [x] All tests pass
