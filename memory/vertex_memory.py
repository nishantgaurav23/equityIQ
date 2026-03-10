"""VertexMemoryBank -- cross-session conversational memory (S16.1).

Stores user preferences, conversation history, prediction outcomes,
and learned agent weights. Uses SQLite locally, with Firestore
production backend as a future enhancement.
"""

import json
import logging
from datetime import datetime, timezone

import aiosqlite

from config.data_contracts import ConversationEntry, PredictionOutcome, UserPreference
from config.settings import get_settings

logger = logging.getLogger(__name__)

_CREATE_PREFERENCES_TABLE = """
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferences_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_CREATE_CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    entry_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    ticker TEXT,
    verdict_session_id TEXT,
    created_at TEXT NOT NULL
);
"""

_CREATE_PREDICTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS prediction_outcomes (
    outcome_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    verdict_session_id TEXT NOT NULL,
    predicted_signal TEXT NOT NULL,
    predicted_confidence REAL NOT NULL,
    price_at_prediction REAL NOT NULL,
    price_at_check REAL,
    actual_return_pct REAL,
    check_window_days INTEGER NOT NULL DEFAULT 30,
    outcome TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    checked_at TEXT
);
"""

_CREATE_WEIGHTS_TABLE = """
CREATE TABLE IF NOT EXISTS learned_weights (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    weights_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations (session_id);",
    "CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations (user_id);",
    "CREATE INDEX IF NOT EXISTS idx_pred_ticker ON prediction_outcomes (ticker);",
    "CREATE INDEX IF NOT EXISTS idx_pred_outcome ON prediction_outcomes (outcome);",
]


class VertexMemoryBank:
    """Cross-session memory bank using SQLite (local) storage.

    Despite the name referencing Vertex AI, the initial implementation uses
    SQLite. Vertex AI integration for semantic search/embeddings is future work.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or get_settings().SQLITE_DB_PATH
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Create database tables and indexes."""
        try:
            conn = await self._get_connection()
            await conn.execute(_CREATE_PREFERENCES_TABLE)
            await conn.execute(_CREATE_CONVERSATIONS_TABLE)
            await conn.execute(_CREATE_PREDICTIONS_TABLE)
            await conn.execute(_CREATE_WEIGHTS_TABLE)
            for idx_sql in _INDEXES:
                await conn.execute(idx_sql)
            await conn.commit()
        except Exception:
            logger.exception("Failed to initialize VertexMemoryBank at %s", self._db_path)
            raise

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            try:
                await self._conn.close()
            except Exception:
                logger.exception("Error closing VertexMemoryBank connection")
            finally:
                self._conn = None

    # -----------------------------------------------------------------------
    # User preferences
    # -----------------------------------------------------------------------

    async def get_preferences(self, user_id: str) -> UserPreference | None:
        """Retrieve user preferences. Returns None if not found or on error."""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT preferences_json FROM user_preferences WHERE user_id = ?",
                (user_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return UserPreference.model_validate_json(row[0])
        except Exception:
            logger.exception("Failed to get preferences for user %s", user_id)
            return None

    async def update_preferences(self, prefs: UserPreference) -> None:
        """Upsert user preferences."""
        try:
            conn = await self._get_connection()
            await conn.execute(
                "INSERT OR REPLACE INTO user_preferences (user_id, preferences_json, updated_at) "
                "VALUES (?, ?, ?)",
                (
                    prefs.user_id,
                    prefs.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await conn.commit()
        except Exception:
            logger.exception("Failed to update preferences for user %s", prefs.user_id)
            raise

    # -----------------------------------------------------------------------
    # Conversation history
    # -----------------------------------------------------------------------

    async def store_conversation_entry(self, entry: ConversationEntry) -> str:
        """Store a conversation entry. Returns the entry_id."""
        try:
            conn = await self._get_connection()
            await conn.execute(
                "INSERT INTO conversations "
                "(entry_id, user_id, session_id, role, content, ticker, "
                "verdict_session_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry.entry_id,
                    entry.user_id,
                    entry.session_id,
                    entry.role,
                    entry.content,
                    entry.ticker,
                    entry.verdict_session_id,
                    entry.created_at.isoformat(),
                ),
            )
            await conn.commit()
            return entry.entry_id
        except Exception:
            logger.exception("Failed to store conversation entry %s", entry.entry_id)
            raise

    async def get_conversation(self, session_id: str, limit: int = 50) -> list[ConversationEntry]:
        """Retrieve conversation entries for a session, ordered by created_at ASC."""
        limit = max(1, min(limit, 200))
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT entry_id, user_id, session_id, role, content, ticker, "
                "verdict_session_id, created_at FROM conversations "
                "WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                ConversationEntry(
                    entry_id=row[0],
                    user_id=row[1],
                    session_id=row[2],
                    role=row[3],
                    content=row[4],
                    ticker=row[5],
                    verdict_session_id=row[6],
                    created_at=row[7],
                )
                for row in rows
            ]
        except Exception:
            logger.exception("Failed to get conversation for session %s", session_id)
            return []

    async def get_user_conversations(
        self, user_id: str, limit: int = 20
    ) -> list[ConversationEntry]:
        """Retrieve recent conversation entries for a user, newest first."""
        limit = max(1, min(limit, 200))
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT entry_id, user_id, session_id, role, content, ticker, "
                "verdict_session_id, created_at FROM conversations "
                "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                ConversationEntry(
                    entry_id=row[0],
                    user_id=row[1],
                    session_id=row[2],
                    role=row[3],
                    content=row[4],
                    ticker=row[5],
                    verdict_session_id=row[6],
                    created_at=row[7],
                )
                for row in rows
            ]
        except Exception:
            logger.exception("Failed to get conversations for user %s", user_id)
            return []

    # -----------------------------------------------------------------------
    # Prediction tracking
    # -----------------------------------------------------------------------

    async def store_prediction(self, prediction: PredictionOutcome) -> str:
        """Store a prediction outcome. Returns the outcome_id."""
        try:
            conn = await self._get_connection()
            await conn.execute(
                "INSERT INTO prediction_outcomes "
                "(outcome_id, ticker, verdict_session_id, predicted_signal, "
                "predicted_confidence, price_at_prediction, price_at_check, "
                "actual_return_pct, check_window_days, outcome, created_at, checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    prediction.outcome_id,
                    prediction.ticker,
                    prediction.verdict_session_id,
                    prediction.predicted_signal,
                    prediction.predicted_confidence,
                    prediction.price_at_prediction,
                    prediction.price_at_check,
                    prediction.actual_return_pct,
                    prediction.check_window_days,
                    prediction.outcome,
                    prediction.created_at.isoformat(),
                    prediction.checked_at.isoformat() if prediction.checked_at else None,
                ),
            )
            await conn.commit()
            return prediction.outcome_id
        except Exception:
            logger.exception("Failed to store prediction %s", prediction.outcome_id)
            raise

    async def get_pending_predictions(self, check_window_days: int = 30) -> list[PredictionOutcome]:
        """Get predictions that are still pending resolution."""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute(
                "SELECT outcome_id, ticker, verdict_session_id, predicted_signal, "
                "predicted_confidence, price_at_prediction, price_at_check, "
                "actual_return_pct, check_window_days, outcome, created_at, checked_at "
                "FROM prediction_outcomes WHERE outcome = 'pending' "
                "ORDER BY created_at ASC",
            )
            rows = await cursor.fetchall()
            return [
                PredictionOutcome(
                    outcome_id=row[0],
                    ticker=row[1],
                    verdict_session_id=row[2],
                    predicted_signal=row[3],
                    predicted_confidence=row[4],
                    price_at_prediction=row[5],
                    price_at_check=row[6],
                    actual_return_pct=row[7],
                    check_window_days=row[8],
                    outcome=row[9],
                    created_at=row[10],
                    checked_at=row[11],
                )
                for row in rows
            ]
        except Exception:
            logger.exception("Failed to get pending predictions")
            return []

    async def update_prediction_outcome(
        self,
        outcome_id: str,
        price_at_check: float,
        actual_return_pct: float,
        outcome: str,
    ) -> bool:
        """Update a prediction with actual results. Returns True if updated."""
        try:
            conn = await self._get_connection()
            checked_at = datetime.now(timezone.utc).isoformat()
            cursor = await conn.execute(
                "UPDATE prediction_outcomes SET price_at_check = ?, actual_return_pct = ?, "
                "outcome = ?, checked_at = ? WHERE outcome_id = ?",
                (price_at_check, actual_return_pct, outcome, checked_at, outcome_id),
            )
            await conn.commit()
            return cursor.rowcount > 0
        except Exception:
            logger.exception("Failed to update prediction %s", outcome_id)
            return False

    async def get_prediction_accuracy(self, ticker: str | None = None) -> dict:
        """Calculate prediction accuracy metrics.

        Returns: {"total": int, "correct": int, "accuracy": float, "by_signal": {...}}
        """
        empty = {"total": 0, "correct": 0, "accuracy": 0.0, "by_signal": {}}
        try:
            conn = await self._get_connection()

            where_clause = "WHERE outcome != 'pending'"
            params: tuple = ()
            if ticker:
                where_clause += " AND ticker = ?"
                params = (ticker,)

            # Total and correct counts
            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM prediction_outcomes {where_clause}",
                params,
            )
            row = await cursor.fetchone()
            total = row[0] if row else 0

            if total == 0:
                return empty

            cursor = await conn.execute(
                f"SELECT COUNT(*) FROM prediction_outcomes {where_clause} AND outcome = 'correct'",
                params,
            )
            row = await cursor.fetchone()
            correct = row[0] if row else 0

            # By signal breakdown
            cursor = await conn.execute(
                f"SELECT predicted_signal, outcome, COUNT(*) "
                f"FROM prediction_outcomes {where_clause} "
                f"GROUP BY predicted_signal, outcome",
                params,
            )
            by_signal: dict[str, dict[str, int]] = {}
            for row in await cursor.fetchall():
                signal = row[0]
                outcome_val = row[1]
                count = row[2]
                if signal not in by_signal:
                    by_signal[signal] = {"total": 0, "correct": 0}
                by_signal[signal]["total"] += count
                if outcome_val == "correct":
                    by_signal[signal]["correct"] += count

            return {
                "total": total,
                "correct": correct,
                "accuracy": correct / total if total > 0 else 0.0,
                "by_signal": by_signal,
            }
        except Exception:
            logger.exception("Failed to calculate prediction accuracy")
            return empty

    # -----------------------------------------------------------------------
    # Learned weights
    # -----------------------------------------------------------------------

    async def get_learned_weights(self) -> dict[str, float] | None:
        """Retrieve learned agent weights. Returns None if not set or on error."""
        try:
            conn = await self._get_connection()
            cursor = await conn.execute("SELECT weights_json FROM learned_weights WHERE id = 1")
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row[0])
        except Exception:
            logger.exception("Failed to get learned weights")
            return None

    async def update_learned_weights(self, weights: dict[str, float]) -> None:
        """Upsert learned agent weights (single-row table)."""
        try:
            conn = await self._get_connection()
            await conn.execute(
                "INSERT OR REPLACE INTO learned_weights (id, weights_json, updated_at) "
                "VALUES (1, ?, ?)",
                (json.dumps(weights), datetime.now(timezone.utc).isoformat()),
            )
            await conn.commit()
        except Exception:
            logger.exception("Failed to update learned weights")
            raise


def get_memory_bank() -> VertexMemoryBank:
    """Factory: returns VertexMemoryBank instance.

    Currently uses SQLite for all environments. Firestore-backed
    VertexMemoryBank is a future enhancement.
    """
    return VertexMemoryBank()
