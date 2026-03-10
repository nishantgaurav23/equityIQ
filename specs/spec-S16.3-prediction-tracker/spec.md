# S16.3 -- Prediction Accuracy Tracker

## Meta
| Field | Value |
|-------|-------|
| Spec ID | S16.3 |
| Title | Prediction Accuracy Tracker |
| Status | done |
| Depends On | S5.2 (HistoryRetriever), S14.3 (Backtester) |
| Produces | `evaluation/prediction_tracker.py`, `tests/test_prediction_tracker.py` |
| Phase | 16 -- Intelligence Layer |

## Context

The system already has:
- **HistoryRetriever** (S5.2): queries past FinalVerdicts from InsightVault
- **Backtester** (S14.3): evaluates verdicts against actual price data with `is_signal_correct()`
- **PredictionOutcome** data contract: already defined in `config/data_contracts.py`
- **SignalFusionModel** with `DEFAULT_WEIGHTS`: agent weighting used for signal synthesis

This spec adds a **PredictionTracker** that continuously evaluates past predictions, tracks per-agent and overall accuracy, and produces weight adjustment recommendations based on historical performance.

## Functional Requirements

### FR-1: PredictionTracker class
- `PredictionTracker(history_retriever, price_lookup, db_path)` -- initializer
- Uses aiosqlite for persistence of prediction outcomes
- Auto-creates `prediction_outcomes` table on init
- Schema: `outcome_id TEXT PRIMARY KEY, ticker TEXT, verdict_session_id TEXT, predicted_signal TEXT, predicted_confidence REAL, price_at_prediction REAL, price_at_check REAL, actual_return_pct REAL, check_window_days INTEGER, outcome TEXT, created_at TEXT, checked_at TEXT`

### FR-2: Track new predictions
- `track_prediction(verdict: FinalVerdict, price_at_prediction: float)` -> PredictionOutcome
- Creates PredictionOutcome entries for each configured window (30, 60, 90 days)
- Stores in SQLite with status "pending"
- Returns the list of created PredictionOutcome objects

### FR-3: Check pending predictions
- `check_pending_predictions()` -> list[PredictionOutcome]
- Queries all "pending" outcomes where `created_at + check_window_days <= now`
- Looks up current price via `price_lookup(ticker, check_date)`
- Computes `actual_return_pct = (price_at_check - price_at_prediction) / price_at_prediction`
- Uses `is_signal_correct()` from backtester to determine outcome ("correct" / "incorrect")
- Updates SQLite record with outcome, price_at_check, actual_return_pct, checked_at
- Returns list of newly resolved outcomes

### FR-4: Accuracy scorecard
- `get_accuracy_scorecard(ticker: str | None = None)` -> AccuracyScorecard
- If ticker is None, returns overall accuracy across all tickers
- If ticker provided, returns accuracy for that specific ticker
- AccuracyScorecard model:
  - `total_predictions: int`
  - `resolved_predictions: int`
  - `pending_predictions: int`
  - `accuracy_by_window: dict[int, float]` -- {30: 0.72, 60: 0.68, 90: 0.65}
  - `accuracy_by_signal: dict[str, float]` -- {"BUY": 0.75, "SELL": 0.60, "HOLD": 0.50}
  - `hit_rate: float` -- overall hit rate across all windows
  - `confidence_calibration: float` -- correlation between confidence and accuracy

### FR-5: Per-agent accuracy tracking
- `get_agent_accuracy()` -> dict[str, AgentAccuracy]
- Tracks which agent signals were correct when the final verdict was correct
- Uses `analyst_signals` from stored FinalVerdicts to attribute accuracy
- AgentAccuracy model:
  - `agent_name: str`
  - `total_signals: int`
  - `correct_signals: int`
  - `accuracy: float`
  - `avg_confidence: float`

### FR-6: Weight adjustment recommendations
- `recommend_weight_adjustments()` -> WeightAdjustment
- Compares per-agent accuracy to current DEFAULT_WEIGHTS
- Agents with higher accuracy get weight boost, lower accuracy get reduction
- Formula: `new_weight = base_weight * (0.5 + agent_accuracy)` then normalize to sum=1.0
- WeightAdjustment model:
  - `current_weights: dict[str, float]`
  - `recommended_weights: dict[str, float]`
  - `agent_accuracies: dict[str, float]`
  - `min_predictions_required: int = 20` -- won't recommend if fewer resolved predictions
  - `confidence: str` -- "high" (50+ predictions), "medium" (20-50), "low" (<20)

### FR-7: Dashboard data endpoint
- `get_scorecard_summary()` -> dict
- Returns a combined summary suitable for frontend rendering:
  - Overall accuracy scorecard
  - Per-agent accuracy breakdown
  - Weight adjustment recommendations
  - Recent prediction outcomes (last 20)

### FR-8: Graceful degradation
- All price lookups wrapped in try/except -- never crash
- If price_lookup returns None, outcome stays "pending"
- If no predictions exist, return zero-value scorecards (not errors)
- Log warnings for failed lookups

## Non-Functional Requirements

- **NFR-1**: All methods are async
- **NFR-2**: Uses aiosqlite for persistence (consistent with InsightVault)
- **NFR-3**: No external API calls in tests -- mock price_lookup
- **NFR-4**: Pydantic v2 models for all return types
- **NFR-5**: Ruff-clean (line-length: 100)

## Data Models (new in this spec)

```python
class AccuracyScorecard(BaseModel):
    total_predictions: int = 0
    resolved_predictions: int = 0
    pending_predictions: int = 0
    accuracy_by_window: dict[int, float] = {}
    accuracy_by_signal: dict[str, float] = {}
    hit_rate: float = 0.0
    confidence_calibration: float = 0.0

class AgentAccuracy(BaseModel):
    agent_name: str
    total_signals: int = 0
    correct_signals: int = 0
    accuracy: float = 0.0
    avg_confidence: float = 0.0

class WeightAdjustment(BaseModel):
    current_weights: dict[str, float] = {}
    recommended_weights: dict[str, float] = {}
    agent_accuracies: dict[str, float] = {}
    min_predictions_required: int = 20
    confidence: str = "low"
```

## Integration Points

- Imports `is_signal_correct` from `evaluation/backtester.py`
- Imports `PredictionOutcome` from `config/data_contracts.py`
- Imports `DEFAULT_WEIGHTS` from `models/signal_fusion.py`
- Uses `HistoryRetriever` for fetching past FinalVerdicts with analyst_signals
- Stores data in SQLite via aiosqlite (same pattern as InsightVault)

## File Map

| File | Purpose |
|------|---------|
| `evaluation/prediction_tracker.py` | PredictionTracker class + data models |
| `tests/test_prediction_tracker.py` | Full test coverage |

## Test Strategy

- Mock `price_lookup` callable
- Mock `HistoryRetriever` for get_ticker_history
- Test track_prediction creates correct number of outcomes
- Test check_pending with mature and immature predictions
- Test accuracy scorecard computation (correct/incorrect/pending mix)
- Test per-agent accuracy attribution
- Test weight adjustment formula and normalization
- Test graceful degradation (price lookup failures, empty data)
- Test edge cases: no predictions, all pending, single prediction
