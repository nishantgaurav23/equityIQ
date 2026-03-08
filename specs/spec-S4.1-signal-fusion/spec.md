# Spec S4.1 -- Signal Fusion (XGBoost Signal Synthesis)

## Overview
SignalFusionModel class that fuses signals from 5 analyst agents into a final BUY/HOLD/SELL/STRONG_BUY/STRONG_SELL verdict using XGBoost. When a trained model is not available, falls back to weighted-average synthesis. Compliance hard override (going_concern / restatement -> SELL) is applied post-prediction regardless of model output.

## Dependencies
- S2.1 (AnalystReport + 6 subclass schemas)
- S2.2 (FinalVerdict + PortfolioInsight)

## Target Location
`models/signal_fusion.py`

---

## Functional Requirements

### FR-1: Feature Extraction
- **What**: `extract_features(reports: list[AnalystReport]) -> dict[str, float]` -- converts a list of analyst reports into a flat feature dictionary suitable for XGBoost input.
- **Inputs**: List of AnalystReport subclasses (ValuationReport, MomentumReport, PulseReport, EconomyReport, ComplianceReport). Up to 5 reports, one per agent type.
- **Outputs**: Dict mapping feature names to float values. Missing reports produce 0.0 for their features plus a `{agent}_missing: 1.0` flag.
- **Features extracted per report type**:
  - ValuationReport: signal_numeric (-1/0/1), confidence, pe_ratio, pb_ratio, revenue_growth, debt_to_equity, fcf_yield, intrinsic_value_gap
  - MomentumReport: signal_numeric, confidence, rsi_14, macd_signal, price_momentum_score, above_sma_50 (0/1), above_sma_200 (0/1)
  - PulseReport: signal_numeric, confidence, sentiment_score, article_count
  - EconomyReport: signal_numeric, confidence, gdp_growth, inflation_rate, fed_funds_rate, unemployment_rate, macro_regime_numeric (expansion=1, recovery=0.5, contraction=-0.5, stagflation=-1)
  - ComplianceReport: signal_numeric, confidence, risk_score, days_since_filing, has_going_concern (0/1), has_restatement (0/1)
- **Edge cases**: None values in report fields -> 0.0. Empty reports list -> all features 0.0 with all missing flags set.

### FR-2: Signal Encoding/Decoding
- **What**: Helper functions to convert between signal strings and numeric values.
  - `signal_to_numeric(signal: str) -> float`: BUY=1.0, HOLD=0.0, SELL=-1.0
  - `numeric_to_signal(value: float, confidence: float) -> str`: Maps numeric prediction back to 5-level signal. Thresholds: value > 0.3 -> BUY, value > 0.3 and confidence >= 0.75 -> STRONG_BUY, value < -0.3 -> SELL, value < -0.3 and confidence >= 0.75 -> STRONG_SELL, else HOLD.
- **Inputs**: Signal string or numeric value + confidence.
- **Outputs**: Numeric float or 5-level signal string.

### FR-3: Weighted Average Fallback
- **What**: `weighted_average_predict(reports: list[AnalystReport]) -> tuple[str, float]` -- fallback when XGBoost model is not trained/loaded.
- **Inputs**: List of AnalystReport subclasses.
- **Outputs**: Tuple of (signal_string, confidence).
- **Weights**: ValuationScout=0.25, MomentumTracker=0.20, PulseMonitor=0.20, EconomyWatcher=0.20, ComplianceChecker=0.15.
- **Logic**: Weighted sum of signal_numeric * confidence * weight. Confidence = weighted average of individual confidences. Missing agent reduces total confidence by 0.20.
- **Edge cases**: No reports -> ("HOLD", 0.0). Single report -> use only that report's signal, confidence * its weight.

### FR-4: XGBoost Model Training
- **What**: `fit(training_data: list[tuple[list[AnalystReport], str]]) -> None` -- trains the XGBoost model on historical data.
- **Inputs**: List of (reports, actual_outcome) tuples where actual_outcome is "BUY"/"HOLD"/"SELL".
- **Outputs**: Stores trained XGBClassifier internally. Sets `self.is_trained = True`.
- **Config**: XGBClassifier with n_estimators=100, max_depth=4, learning_rate=0.1, objective='multi:softprob', num_class=3.
- **Edge cases**: Empty training data -> raise ValueError. <10 samples -> log warning but proceed.

### FR-5: XGBoost Prediction
- **What**: `predict(reports: list[AnalystReport]) -> FinalVerdict` -- runs prediction using trained model or fallback.
- **Inputs**: List of AnalystReport subclasses for a single ticker.
- **Outputs**: FinalVerdict with all fields populated.
- **Logic**:
  1. Extract features from reports
  2. If model is trained: use XGBoost predict_proba for signal + max probability as confidence base
  3. If model not trained: use weighted_average_predict fallback
  4. Apply compliance hard override (FR-6)
  5. Populate FinalVerdict: ticker (from first report), final_signal, overall_confidence, analyst_signals dict, key_drivers list, session_id (uuid4)
- **Edge cases**: Empty reports -> FinalVerdict with HOLD signal, 0.0 confidence.

### FR-6: Compliance Hard Override
- **What**: `apply_compliance_override(verdict: FinalVerdict, compliance_report: ComplianceReport | None) -> FinalVerdict` -- forces SELL if going_concern or restatement detected.
- **Inputs**: FinalVerdict and optional ComplianceReport.
- **Outputs**: Modified FinalVerdict (signal forced to SELL, key_drivers updated).
- **Logic**: If compliance_report has "going_concern" or "restatement" in risk_flags -> override final_signal to "SELL", append reason to key_drivers.
- **Edge cases**: No compliance report -> no override. Empty risk_flags -> no override.

### FR-7: SignalFusionModel Class
- **What**: Main class encapsulating all functionality.
- **Attributes**: `model` (XGBClassifier | None), `is_trained` (bool), `weights` (dict), `label_encoder` (maps BUY/HOLD/SELL to 0/1/2).
- **Methods**: `extract_features()`, `fit()`, `predict()`, `weighted_average_predict()`, `apply_compliance_override()`, `signal_to_numeric()`, `numeric_to_signal()`.
- **Constructor**: `__init__(weights: dict | None = None)` -- accepts optional custom weights, defaults to standard weights.

---

## Tangible Outcomes

- [ ] **Outcome 1**: `from models.signal_fusion import SignalFusionModel` works
- [ ] **Outcome 2**: `extract_features()` produces correct feature dict from mixed report types
- [ ] **Outcome 3**: Weighted average fallback returns valid signal+confidence without trained model
- [ ] **Outcome 4**: `fit()` trains XGBoost model on sample data, `is_trained` becomes True
- [ ] **Outcome 5**: `predict()` returns valid FinalVerdict with all required fields
- [ ] **Outcome 6**: Compliance override forces SELL on going_concern/restatement
- [ ] **Outcome 7**: STRONG_BUY/STRONG_SELL only when confidence >= 0.75
- [ ] **Outcome 8**: Missing agents reduce confidence by 0.20 in fallback mode

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_signal_to_numeric**: BUY->1.0, HOLD->0.0, SELL->-1.0
2. **test_numeric_to_signal**: Thresholds for all 5 signal levels
3. **test_extract_features_single_report**: One ValuationReport -> correct feature dict
4. **test_extract_features_all_reports**: All 5 report types -> complete feature dict
5. **test_extract_features_missing_reports**: 3 of 5 reports -> missing flags set
6. **test_extract_features_none_fields**: Report with None fields -> 0.0 values
7. **test_weighted_average_all_buy**: All agents BUY -> BUY signal
8. **test_weighted_average_all_sell**: All agents SELL -> SELL signal
9. **test_weighted_average_mixed**: Mixed signals -> correct weighted result
10. **test_weighted_average_missing_agents**: <5 reports -> confidence reduced
11. **test_weighted_average_empty**: No reports -> HOLD, 0.0
12. **test_fit_trains_model**: fit() with sample data -> is_trained=True
13. **test_fit_empty_data**: Empty list -> ValueError
14. **test_predict_with_trained_model**: After fit(), predict() uses XGBoost
15. **test_predict_without_model**: No training -> uses weighted average fallback
16. **test_predict_returns_final_verdict**: Output is FinalVerdict instance
17. **test_compliance_override_going_concern**: going_concern -> SELL
18. **test_compliance_override_restatement**: restatement -> SELL
19. **test_compliance_override_no_flags**: No risk flags -> no change
20. **test_compliance_override_none_report**: No ComplianceReport -> no change
21. **test_strong_buy_requires_high_confidence**: confidence >= 0.75 required
22. **test_strong_sell_requires_high_confidence**: confidence >= 0.75 required
23. **test_custom_weights**: Custom weights passed to constructor work correctly
24. **test_predict_populates_all_verdict_fields**: session_id, analyst_signals, key_drivers all set

### Mocking Strategy
- No external services to mock -- this is pure ML/math
- XGBoost model itself is tested with real training (small sample data)
- Use pytest fixtures for sample AnalystReport instances

### Coverage Expectation
- All public methods have at least one test
- Edge cases: empty inputs, None fields, missing agents, threshold boundaries
- 24+ tests covering all FRs

---

## References
- roadmap.md (S4.1 row), design.md
- config/data_contracts.py (AnalystReport, FinalVerdict schemas)
- Signal weighting: ValuationScout=0.25, MomentumTracker=0.20, PulseMonitor=0.20, EconomyWatcher=0.20, ComplianceChecker=0.15
