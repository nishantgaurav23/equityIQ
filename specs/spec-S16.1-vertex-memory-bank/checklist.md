# S16.1 -- Vertex AI Memory Bank Checklist

## Pydantic Models
- [x] `UserPreference` model in `config/data_contracts.py`
- [x] `ConversationEntry` model in `config/data_contracts.py`
- [x] `PredictionOutcome` model in `config/data_contracts.py`
- [x] Field validators (confidence clamping, etc.)

## Core Implementation
- [x] `memory/vertex_memory.py` -- VertexMemoryBank class
- [x] `initialize()` -- create SQLite tables with indexes
- [x] `close()` -- clean shutdown
- [x] `get_preferences()` / `update_preferences()` -- user prefs CRUD
- [x] `store_conversation_entry()` -- append conversation turn
- [x] `get_conversation()` -- retrieve by session_id
- [x] `get_user_conversations()` -- retrieve by user_id
- [x] `store_prediction()` -- record prediction at analysis time
- [x] `get_pending_predictions()` -- find predictions awaiting check
- [x] `update_prediction_outcome()` -- update with actual price data
- [x] `get_prediction_accuracy()` -- calculate accuracy metrics
- [x] `get_learned_weights()` / `update_learned_weights()` -- weight persistence
- [x] `get_memory_bank()` factory function

## Error Handling
- [x] All public methods wrapped in try/except
- [x] Failures return empty/None, never crash
- [x] Logging on all exceptions

## Integration
- [x] Export from `memory/__init__.py`
- [x] Settings: no new env vars needed (uses existing ENVIRONMENT, SQLITE_DB_PATH)

## Tests
- [x] `tests/test_vertex_memory.py` created
- [x] Test initialize and close
- [x] Test user preferences CRUD
- [x] Test conversation storage and retrieval
- [x] Test prediction storage and tracking
- [x] Test prediction accuracy calculation
- [x] Test learned weights persistence
- [x] Test factory function
- [x] Test error handling (graceful degradation)
- [x] All tests pass with `pytest tests/test_vertex_memory.py -v`

## Quality
- [x] Ruff lint clean
- [x] No hardcoded secrets
- [x] Async everywhere
