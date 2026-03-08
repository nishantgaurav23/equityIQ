# Spec S5.3 -- Firestore Backend

## Overview
Firestore-backed storage backend for production deployment on GCP. Implements the same interface as InsightVault (S5.1) but uses Google Cloud Firestore instead of SQLite. The backend is selected via the `ENVIRONMENT` env var (`"production"` -> Firestore, otherwise -> SQLite). Optional -- only needed for GCP deployment.

## Dependencies
- S5.1 (InsightVault -- SQLite session storage) -- must be `done`

## Target Location
- `memory/firestore_vault.py`

---

## Functional Requirements

### FR-1: FirestoreVault class with same interface as InsightVault
- **What**: `FirestoreVault` class that implements `initialize()`, `store_verdict()`, `get_verdict()`, `list_verdicts()`, `delete_verdict()`, and `close()` -- matching the InsightVault API exactly
- **Inputs/Outputs**: Same signatures as InsightVault methods
- **Edge cases**: Firestore client unavailable, network errors, empty collections

### FR-2: initialize() -- Firestore client setup
- **What**: Create async Firestore client, verify connectivity. Collection name: `verdicts`
- **Inputs**: GCP_PROJECT_ID from settings (required for Firestore)
- **Outputs**: Firestore client ready for operations
- **Edge cases**: Missing GCP_PROJECT_ID raises clear error, connection failure logged

### FR-3: store_verdict(verdict) -- Store FinalVerdict document
- **What**: Store a FinalVerdict as a Firestore document in the `verdicts` collection. Document ID = session_id. Generate session_id (uuid4) if not provided
- **Inputs**: `FinalVerdict` object
- **Outputs**: Returns `session_id` (str)
- **Edge cases**: Firestore write failure -> log and raise, duplicate session_id overwrites

### FR-4: get_verdict(session_id) -- Retrieve single verdict
- **What**: Fetch document by session_id from `verdicts` collection
- **Inputs**: `session_id: str`
- **Outputs**: `FinalVerdict | None`
- **Edge cases**: Document not found -> return None, Firestore read error -> log and return None

### FR-5: list_verdicts(ticker, limit, offset) -- Query verdicts
- **What**: List verdicts ordered by `created_at` DESC, optionally filtered by ticker. Limit capped at 200
- **Inputs**: `ticker: str | None`, `limit: int = 50`, `offset: int = 0`
- **Outputs**: `list[FinalVerdict]`
- **Edge cases**: Empty collection -> empty list, Firestore query error -> log and return []

### FR-6: delete_verdict(session_id) -- Delete single verdict
- **What**: Delete document by session_id from `verdicts` collection
- **Inputs**: `session_id: str`
- **Outputs**: `bool` (True if deleted, False if not found)
- **Edge cases**: Document not found -> return False, Firestore delete error -> log and return False

### FR-7: close() -- Clean up Firestore client
- **What**: Close Firestore client connection gracefully
- **Edge cases**: Already closed -> no-op, error during close -> log and suppress

### FR-8: get_vault() factory function
- **What**: Factory function that returns `FirestoreVault` if `ENVIRONMENT == "production"`, otherwise returns `InsightVault`. This is the single selection point for the memory backend
- **Inputs**: None (reads from settings)
- **Outputs**: `InsightVault | FirestoreVault` instance

---

## Tangible Outcomes

- [ ] **Outcome 1**: `FirestoreVault` class exists in `memory/firestore_vault.py` with all 6 methods matching InsightVault interface
- [ ] **Outcome 2**: `get_vault()` factory returns FirestoreVault when `ENVIRONMENT=production`, InsightVault otherwise
- [ ] **Outcome 3**: `store_verdict()` stores FinalVerdict and returns session_id
- [ ] **Outcome 4**: `get_verdict()` retrieves stored verdict by session_id
- [ ] **Outcome 5**: `list_verdicts()` returns filtered, paginated results ordered by created_at DESC
- [ ] **Outcome 6**: `delete_verdict()` removes document and returns True/False
- [ ] **Outcome 7**: All external Firestore calls wrapped in try/except -- never crashes
- [ ] **Outcome 8**: All tests pass with Firestore client fully mocked

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_initialize_creates_client**: FirestoreVault.initialize() creates Firestore client with correct project_id
2. **test_initialize_missing_project_id**: Raises ValueError when GCP_PROJECT_ID is empty
3. **test_store_verdict_returns_session_id**: store_verdict() stores doc and returns session_id
4. **test_store_verdict_generates_session_id**: Generates uuid4 when verdict.session_id is empty
5. **test_get_verdict_found**: get_verdict() returns FinalVerdict for existing session_id
6. **test_get_verdict_not_found**: get_verdict() returns None for missing session_id
7. **test_get_verdict_firestore_error**: get_verdict() returns None on Firestore error
8. **test_list_verdicts_all**: list_verdicts() returns all verdicts ordered by created_at DESC
9. **test_list_verdicts_by_ticker**: list_verdicts(ticker="AAPL") filters correctly
10. **test_list_verdicts_limit_cap**: limit capped at 200
11. **test_list_verdicts_firestore_error**: Returns empty list on error
12. **test_delete_verdict_found**: delete_verdict() returns True when doc exists
13. **test_delete_verdict_not_found**: delete_verdict() returns False when doc missing
14. **test_close_cleans_up**: close() closes client, subsequent calls safe
15. **test_get_vault_production**: get_vault() returns FirestoreVault when ENVIRONMENT=production
16. **test_get_vault_local**: get_vault() returns InsightVault when ENVIRONMENT=local

### Mocking Strategy
- Mock `google.cloud.firestore.AsyncClient` entirely -- no real Firestore calls in tests
- Use `unittest.mock.AsyncMock` for async Firestore operations
- Mock `get_settings()` to control ENVIRONMENT and GCP_PROJECT_ID

### Coverage Expectation
- All public methods tested with happy path and error cases
- Factory function tested for both environment values

---

## References
- `memory/insight_vault.py` -- interface to match
- `config/settings.py` -- ENVIRONMENT and GCP_PROJECT_ID settings
- `roadmap.md`, `design.md`
