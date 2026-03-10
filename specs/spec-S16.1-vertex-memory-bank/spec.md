# S16.1 -- Vertex AI Memory Bank

## Overview
Cross-session conversational memory using Vertex AI. Stores user preferences, past interactions, and prediction outcomes. Enables the system to learn from historical predictions and improve signal weights over time.

## Location
`memory/vertex_memory.py`

## Dependencies
- S5.3 (Firestore backend) -- same memory layer pattern
- S8.2 (Market conductor) -- orchestrator that stores verdicts

## Background
The existing memory layer has InsightVault (SQLite, local) and FirestoreVault (Firestore, production) for storing FinalVerdict objects. VertexMemoryBank adds a higher-level conversational memory that:
1. Tracks user preferences (favorite tickers, risk tolerance, preferred analysis depth)
2. Stores conversation context (what the user asked, what was returned)
3. Records prediction outcomes (what we predicted vs what happened)
4. Enables weight adjustment based on historical prediction accuracy

## Design

### Pydantic Models (in `config/data_contracts.py`)

```python
class UserPreference(BaseModel):
    """User-level preferences persisted across sessions."""
    user_id: str
    favorite_tickers: list[str] = []
    risk_tolerance: Literal["conservative", "moderate", "aggressive"] = "moderate"
    preferred_agents: list[str] = []
    notification_enabled: bool = False
    updated_at: datetime

class ConversationEntry(BaseModel):
    """Single turn in a conversation."""
    entry_id: str
    user_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    ticker: str | None = None
    verdict_session_id: str | None = None  # Links to stored FinalVerdict
    created_at: datetime

class PredictionOutcome(BaseModel):
    """Tracks predicted signal vs actual price movement."""
    outcome_id: str
    ticker: str
    verdict_session_id: str
    predicted_signal: str  # STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
    predicted_confidence: float
    price_at_prediction: float
    price_at_check: float | None = None
    actual_return_pct: float | None = None
    check_window_days: int = 30
    outcome: Literal["correct", "incorrect", "pending"] = "pending"
    created_at: datetime
    checked_at: datetime | None = None
```

### VertexMemoryBank Class (`memory/vertex_memory.py`)

```python
class VertexMemoryBank:
    """Cross-session memory using SQLite (local) or Firestore (production).

    Despite the name referencing Vertex AI, the initial implementation uses
    the same storage backends as the existing memory layer. Vertex AI
    integration for semantic search and embeddings is a future enhancement.
    """

    async def initialize(self) -> None
    async def close(self) -> None

    # User preferences
    async def get_preferences(self, user_id: str) -> UserPreference | None
    async def update_preferences(self, prefs: UserPreference) -> None

    # Conversation history
    async def store_conversation_entry(self, entry: ConversationEntry) -> str
    async def get_conversation(self, session_id: str, limit: int = 50) -> list[ConversationEntry]
    async def get_user_conversations(self, user_id: str, limit: int = 20) -> list[ConversationEntry]

    # Prediction tracking
    async def store_prediction(self, prediction: PredictionOutcome) -> str
    async def get_pending_predictions(self, check_window_days: int = 30) -> list[PredictionOutcome]
    async def update_prediction_outcome(self, outcome_id: str, price_at_check: float, actual_return_pct: float, outcome: str) -> bool
    async def get_prediction_accuracy(self, ticker: str | None = None, agent_name: str | None = None) -> dict

    # Weight learning
    async def get_learned_weights(self) -> dict[str, float] | None
    async def update_learned_weights(self, weights: dict[str, float]) -> None
```

### SQLite Tables (local mode)

```sql
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferences_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

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

CREATE TABLE IF NOT EXISTS learned_weights (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    weights_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### Storage Backend Selection

Same pattern as existing vault: `ENVIRONMENT == 'production'` -> Firestore collections, otherwise SQLite.

### Key Behaviors

1. **User preferences**: CRUD with upsert semantics. `user_id` = "default" for anonymous users.
2. **Conversation storage**: Append-only log. Each entry tagged with session_id for grouping.
3. **Prediction tracking**: Store at analysis time. Update when price data is available. Calculate accuracy metrics.
4. **Weight learning**: Single-row table storing the latest learned agent weights. Used by SignalSynthesizer as override.
5. **Prediction accuracy**: Returns `{ "total": int, "correct": int, "accuracy": float, "by_signal": { ... } }`
6. **Graceful degradation**: All methods wrapped in try/except. Failures log and return empty/None -- never crash.
7. **TTL-free**: Memory is persistent. No cache expiration on stored data.

## Acceptance Criteria

1. `VertexMemoryBank` class with full CRUD for preferences, conversations, predictions, and weights
2. All 3 Pydantic models validated and clamped
3. SQLite backend with proper indexes
4. Factory function `get_memory_bank()` returns appropriate backend
5. All external calls wrapped in try/except
6. 100% test coverage on all public methods
7. Tests use in-memory SQLite (`:memory:`)
8. Integrates with existing memory layer (imports in `memory/__init__.py`)
