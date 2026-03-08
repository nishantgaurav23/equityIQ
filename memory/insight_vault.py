"""InsightVault -- async SQLite storage for FinalVerdict objects."""

import logging
import os
import uuid
from datetime import datetime, timezone

import aiosqlite

from config.data_contracts import FinalVerdict
from config.settings import get_settings

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS verdicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    verdict_json TEXT NOT NULL,
    final_signal TEXT NOT NULL,
    overall_confidence REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""

_CREATE_SESSION_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_verdicts_session_id ON verdicts (session_id);"
)
_CREATE_TICKER_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_verdicts_ticker ON verdicts (ticker);"


class InsightVault:
    """Async SQLite-backed storage for analysis verdicts."""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or get_settings().SQLITE_DB_PATH
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database directory and tables if they don't exist."""
        try:
            parent = os.path.dirname(self._db_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            conn = await self._get_connection()
            await conn.execute(_CREATE_TABLE_SQL)
            await conn.execute(_CREATE_SESSION_INDEX_SQL)
            await conn.execute(_CREATE_TICKER_INDEX_SQL)
            await conn.commit()
        except Exception:
            logger.exception("Failed to initialize InsightVault at %s", self._db_path)
            raise

    async def _get_connection(self) -> aiosqlite.Connection:
        """Return existing or create new aiosqlite connection."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def store_verdict(self, verdict: FinalVerdict) -> str:
        """Store a FinalVerdict. Returns the session_id (generated if empty)."""
        session_id = verdict.session_id or str(uuid.uuid4())
        verdict.session_id = session_id
        created_at = datetime.now(timezone.utc).isoformat()

        verdict_json = verdict.model_dump_json()

        try:
            conn = await self._get_connection()
            await conn.execute(
                """INSERT INTO verdicts
                   (session_id, ticker, verdict_json, final_signal, overall_confidence, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    verdict.ticker,
                    verdict_json,
                    verdict.final_signal,
                    verdict.overall_confidence,
                    created_at,
                ),
            )
            await conn.commit()
        except Exception:
            logger.exception("Failed to store verdict for session %s", session_id)
            raise

        return session_id

    async def get_verdict(self, session_id: str) -> FinalVerdict | None:
        """Retrieve a single verdict by session_id. Returns None if not found."""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT verdict_json FROM verdicts WHERE session_id = ? LIMIT 1",
                (session_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return FinalVerdict.model_validate_json(row[0])
        except Exception:
            logger.exception("Failed to get verdict for session %s", session_id)
            return None

    async def list_verdicts(
        self,
        ticker: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FinalVerdict]:
        """List verdicts, optionally filtered by ticker. Ordered by created_at DESC."""
        limit = min(limit, 200)

        try:
            conn = await self._get_connection()
            if ticker:
                cursor = await conn.execute(
                    "SELECT verdict_json FROM verdicts WHERE ticker = ? "
                    "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (ticker, limit, offset),
                )
            else:
                cursor = await conn.execute(
                    "SELECT verdict_json FROM verdicts ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            rows = await cursor.fetchall()
            return [FinalVerdict.model_validate_json(row[0]) for row in rows]
        except Exception:
            logger.exception("Failed to list verdicts")
            return []

    async def delete_verdict(self, session_id: str) -> bool:
        """Delete a verdict by session_id. Returns True if deleted, False if not found."""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "DELETE FROM verdicts WHERE session_id = ?",
                (session_id,),
            )
            await conn.commit()
            return cursor.rowcount > 0
        except Exception:
            logger.exception("Failed to delete verdict for session %s", session_id)
            return False

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                logger.exception("Error closing InsightVault connection")
            finally:
                self._conn = None
