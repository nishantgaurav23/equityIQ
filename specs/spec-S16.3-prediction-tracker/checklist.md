# S16.3 -- Prediction Tracker Checklist

## Models
- [x] AccuracyScorecard Pydantic model
- [x] AgentAccuracy Pydantic model
- [x] WeightAdjustment Pydantic model

## PredictionTracker Core
- [x] FR-1: __init__ with aiosqlite, auto-create prediction_outcomes table
- [x] FR-2: track_prediction() -- creates PredictionOutcome for 30/60/90 day windows
- [x] FR-3: check_pending_predictions() -- resolves mature pending outcomes
- [x] FR-4: get_accuracy_scorecard() -- overall and per-ticker accuracy
- [x] FR-5: get_agent_accuracy() -- per-agent hit rate using analyst_signals
- [x] FR-6: recommend_weight_adjustments() -- accuracy-based weight tuning
- [x] FR-7: get_scorecard_summary() -- combined dashboard data
- [x] FR-8: Graceful degradation -- try/except on all external calls

## Tests
- [x] test_track_prediction_creates_outcomes
- [x] test_check_pending_resolves_mature
- [x] test_check_pending_skips_immature
- [x] test_accuracy_scorecard_computation
- [x] test_accuracy_scorecard_per_ticker
- [x] test_agent_accuracy_attribution
- [x] test_weight_adjustment_formula
- [x] test_weight_adjustment_insufficient_data
- [x] test_scorecard_summary_combined
- [x] test_graceful_degradation_price_failure
- [x] test_empty_data_returns_zero_scorecard

## Quality
- [x] ruff check passes
- [x] All tests pass
- [x] Checklist fully checked
- [x] Roadmap status updated to done
