# Spec S2.3 -- Agent Personas

## Overview
Define system prompts for all 7 specialist agents as a `PERSONAS` dictionary in `config/analyst_personas.py`. Each persona string defines the agent's domain expertise, expected output format, analytical constraints, and behavioral rules. These prompts are injected into the Gemini LLM at agent initialization (consumed by `BaseAnalystAgent` in Phase 6).

## Dependencies
- None (standalone module -- no imports from other project modules)

## Target Location
- `config/analyst_personas.py`

---

## Functional Requirements

### FR-1: PERSONAS dictionary
- **What**: Module-level `PERSONAS: dict[str, str]` mapping agent names to system prompt strings
- **Keys** (7 total):
  - `"valuation_scout"`
  - `"momentum_tracker"`
  - `"pulse_monitor"`
  - `"economy_watcher"`
  - `"compliance_checker"`
  - `"signal_synthesizer"`
  - `"risk_guardian"`
- **Value**: Each value is a non-empty string containing the agent's system prompt

### FR-2: ValuationScout persona
- **Domain**: Fundamental stock valuation -- P/E, P/B, revenue growth, debt/equity, FCF yield, intrinsic value gap
- **Output schema**: ValuationReport
- **Signal logic**: BUY if undervalued (intrinsic_value_gap > 0), SELL if overvalued, HOLD if fairly valued
- **Constraints**: Must reference specific valuation ratios in reasoning. Must handle missing data gracefully (nullable fields)

### FR-3: MomentumTracker persona
- **Domain**: Technical analysis -- RSI, MACD, SMA crossovers, volume trends, price momentum
- **Output schema**: MomentumReport
- **Signal logic**: BUY on bullish signals (RSI < 30 oversold bounce, MACD crossover, above SMA 50/200), SELL on bearish
- **Constraints**: Must consider multiple indicators, not just one. Price momentum score [-1, 1]

### FR-4: PulseMonitor persona
- **Domain**: News sentiment analysis, event detection (earnings, mergers, lawsuits, FDA approvals)
- **Output schema**: PulseReport
- **Signal logic**: BUY on strong positive sentiment + bullish events, SELL on negative sentiment + bearish events
- **Constraints**: NEVER assign confidence > 0.70 with fewer than 3 articles. Must flag detected events

### FR-5: EconomyWatcher persona
- **Domain**: Macroeconomic indicators -- GDP growth, inflation, Fed funds rate, unemployment, macro regime classification
- **Output schema**: EconomyReport
- **Signal logic**: BUY in expansion/recovery, SELL in contraction/stagflation, HOLD in transition
- **Constraints**: Must classify macro_regime. Must consider how macro environment impacts the specific stock sector

### FR-6: ComplianceChecker persona
- **Domain**: SEC filings analysis, regulatory risk detection
- **Output schema**: ComplianceReport
- **Signal logic**: SELL if going_concern or restatement detected (hard override). Otherwise signal based on filing recency and risk score
- **Constraints**: going_concern or restatement in risk_flags ALWAYS forces SELL signal. Must check filing timeliness

### FR-7: SignalSynthesizer persona
- **Domain**: Multi-signal fusion -- combines all analyst reports into a final verdict
- **Output schema**: FinalVerdict (5-level: STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
- **Signal logic**: Weighted combination of analyst signals. STRONG_BUY/STRONG_SELL requires confidence >= 0.75
- **Constraints**: Must apply compliance override. Must explain key drivers. Default weights: Valuation 0.25, Momentum 0.20, Pulse 0.20, Economy 0.20, Compliance 0.15

### FR-8: RiskGuardian persona
- **Domain**: Portfolio risk assessment -- beta, volatility, Sharpe ratio, max drawdown, VaR, position sizing
- **Output schema**: RiskGuardianReport
- **Signal logic**: Provides risk assessment (not directional signal). BUY = low risk, SELL = high risk, HOLD = moderate
- **Constraints**: suggested_position_size NEVER exceeds 0.10 (10% max per stock). Must calculate position size based on volatility

---

## Tangible Outcomes

- [ ] **Outcome 1**: `config/analyst_personas.py` exists and is importable
- [ ] **Outcome 2**: `PERSONAS` is a dict with exactly 7 keys
- [ ] **Outcome 3**: All 7 required agent names are present as keys
- [ ] **Outcome 4**: Every persona value is a non-empty string (len > 50 chars -- real prompts, not stubs)
- [ ] **Outcome 5**: ValuationScout persona mentions P/E, intrinsic value, and valuation ratios
- [ ] **Outcome 6**: PulseMonitor persona contains the confidence cap rule (< 3 articles -> max 0.70)
- [ ] **Outcome 7**: ComplianceChecker persona contains the going_concern/restatement SELL override rule
- [ ] **Outcome 8**: RiskGuardian persona contains the 10% max position size rule
- [ ] **Outcome 9**: SignalSynthesizer persona mentions the 0.75 confidence threshold for STRONG signals
- [ ] **Outcome 10**: PERSONAS dict is importable via `from config.analyst_personas import PERSONAS`

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_personas_importable**: `from config.analyst_personas import PERSONAS` succeeds
2. **test_personas_is_dict**: PERSONAS is a dict
3. **test_personas_has_seven_keys**: len(PERSONAS) == 7
4. **test_personas_required_keys**: All 7 agent names present
5. **test_personas_values_are_strings**: Every value is a str
6. **test_personas_values_non_empty**: Every value has len > 50
7. **test_valuation_scout_content**: Contains "P/E" or "pe_ratio" and "intrinsic" or "valuation"
8. **test_pulse_monitor_confidence_rule**: Contains "0.70" or "0.7" and ("3 articles" or "fewer than 3" or "article_count")
9. **test_compliance_checker_override_rule**: Contains "going_concern" and "restatement" and "SELL"
10. **test_risk_guardian_position_limit**: Contains "0.10" or "10%" and "position"
11. **test_signal_synthesizer_strong_threshold**: Contains "0.75" and ("STRONG" or "strong")
12. **test_each_persona_mentions_output_schema**: Each persona references its expected output schema name

### Mocking Strategy
- No external services -- pure dictionary of strings, no mocking needed

### Coverage Expectation
- All 7 personas tested for existence, type, content keywords
- Critical business rules (confidence cap, SELL override, position limit, STRONG threshold) verified in prompt text

---

## References
- roadmap.md (Phase 2, S2.3)
- CLAUDE.md (The 7 Agents table, Signal Weighting, Key Design Decisions)
- config/data_contracts.py (output schemas referenced by personas)
