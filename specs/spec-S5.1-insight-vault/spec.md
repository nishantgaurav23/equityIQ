# S5.1 -- InsightVault (SQLite Session Storage)

## Goal
Implement `memory/insight_vault.py` -- an async SQLite-backed storage layer for persisting analysis verdicts and session data.

## Dependencies
| Spec | Artifact | Status |
|------|----------|--------|
| S1.3 | `config/settings.py` | done |
| S2.2 | `config/data_contracts.py` | done |

## Artifact
`memory/insight_vault.py`

## Test File
`tests/test_insight_vault.py`

## What It Does
InsightVault provides async CRUD operations for `FinalVerdict` objects, backed by SQLite via `aiosqlite`. It auto-creates the database and tables on initialization. Used by `MarketConductor` to persist analysis results and by API endpoints to retrieve historical analyses.

## Schema

### Table: `verdicts`
| Column | Type | Constraints |
|--------|------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT |
| `session_id` | TEXT | NOT NULL, INDEX |
| `ticker` | TEXT | NOT NULL, INDEX |
| `verdict_json` | TEXT | NOT NULL (JSON-serialized FinalVerdict) |
| `final_signal` | TEXT | NOT NULL |
| `overall_confidence` | REAL | NOT NULL |
| `created_at` | TEXT | NOT NULL (ISO 8601 UTC) |

## Class Interface

```python
class InsightVault:
    def __init__(self, db_path: str | None = None):
        """Initialize with db_path. Defaults to Settings().SQLITE_DB_PATH."""

    async def initialize(self) -> None:
        """Create database directory and tables if they don't exist."""

    async def store_verdict(self, verdict: FinalVerdict) -> str:
        """Store a FinalVerdict. Returns the session_id (generated if empty)."""

    async def get_verdict(self, session_id: str) -> FinalVerdict | None:
        """Retrieve a single verdict by session_id. Returns None if not found."""

    async def list_verdicts(
        self,
        ticker: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FinalVerdict]:
        """List verdicts, optionally filtered by ticker. Ordered by created_at DESC."""

    async def delete_verdict(self, session_id: str) -> bool:
        """Delete a verdict by session_id. Returns True if deleted, False if not found."""

    async def close(self) -> None:
        """Close the database connection."""
```

## Design Decisions

1. **aiosqlite for async** -- non-blocking SQLite access, matches project async-everywhere pattern
2. **JSON serialization** -- store full FinalVerdict as JSON text, plus denormalized columns for filtering/indexing
3. **Auto-create on init** -- `initialize()` creates parent dirs + tables with `IF NOT EXISTS`
4. **Session ID generation** -- if `verdict.session_id` is empty, generate a UUID4
5. **Settings integration** -- default db_path from `Settings().SQLITE_DB_PATH` but overridable for testing
6. **Connection management** -- lazy connection (connect on first operation), explicit `close()`

## Constraints
- All methods are `async`
- Never crash on DB errors -- wrap in try/except, log errors, return sensible defaults
- Use parameterized queries (no SQL injection)
- Limit param capped at 200 max
- FinalVerdict round-trip must be lossless (serialize -> deserialize -> identical)

## Tangible Outcomes
1. `memory/insight_vault.py` exists with InsightVault class
2. `memory/__init__.py` exports InsightVault
3. All tests pass: store, retrieve, list (with/without filter), delete, auto-init, error handling
4. `ruff check` and `ruff format` pass
5. Round-trip test: store a FinalVerdict, retrieve it, assert equality
