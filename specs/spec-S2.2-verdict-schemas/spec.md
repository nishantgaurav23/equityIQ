# Spec S2.2 -- Verdict Schemas

## Overview
Define `FinalVerdict` and `PortfolioInsight` Pydantic v2 models. FinalVerdict is the output of the SignalSynthesizer -- a 5-level signal (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL) with confidence, analyst signals, risk summary, and key drivers. PortfolioInsight aggregates multiple FinalVerdicts for multi-stock analysis.

## Dependencies
- S2.1 (analyst-report-schemas) -- AnalystReport and subclasses must exist in `config/data_contracts.py`

## Target Location
- `config/data_contracts.py` (append to existing file)

---

## Functional Requirements

### FR-1: FinalVerdict model
- **What**: Pydantic BaseModel representing the synthesized output of all analyst agents
- **Fields**:
  - `ticker: str` -- stock symbol
  - `final_signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]` -- 5-level directional signal
  - `overall_confidence: float` -- clamped [0.0, 1.0] via field_validator
  - `price_target: float | None` -- estimated price target (nullable)
  - `analyst_signals: dict[str, str]` -- map of agent_name -> signal (e.g. {"valuation_scout": "BUY"})
  - `risk_summary: str` -- summary of risk assessment
  - `key_drivers: list[str]` -- top reasons for the verdict
  - `session_id: str` -- unique session identifier for tracing
  - `timestamp: datetime` -- defaults to utcnow
- **Validation rules**:
  - STRONG_BUY/STRONG_SELL requires overall_confidence >= 0.75. If confidence < 0.75, downgrade to BUY/SELL respectively.
  - overall_confidence clamped to [0.0, 1.0]

### FR-2: PortfolioInsight model
- **What**: Pydantic BaseModel aggregating multiple FinalVerdicts for portfolio analysis
- **Fields**:
  - `tickers: list[str]` -- list of analyzed stock symbols
  - `verdicts: list[FinalVerdict]` -- individual verdicts for each ticker
  - `portfolio_signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]` -- aggregate signal
  - `diversification_score: float` -- clamped [0.0, 1.0]
  - `top_pick: str | None` -- ticker of the top-ranked stock (nullable)
  - `timestamp: datetime` -- defaults to utcnow
- **Validation rules**:
  - diversification_score clamped to [0.0, 1.0]

---

## Tangible Outcomes

- [ ] **Outcome 1**: FinalVerdict and PortfolioInsight exist in `config/data_contracts.py` and are importable
- [ ] **Outcome 2**: FinalVerdict can be instantiated with valid data, all fields populated correctly
- [ ] **Outcome 3**: FinalVerdict.overall_confidence clamped to [0, 1]
- [ ] **Outcome 4**: STRONG_BUY with confidence < 0.75 is downgraded to BUY
- [ ] **Outcome 5**: STRONG_SELL with confidence < 0.75 is downgraded to SELL
- [ ] **Outcome 6**: BUY/HOLD/SELL signals pass through regardless of confidence
- [ ] **Outcome 7**: PortfolioInsight can be instantiated with a list of FinalVerdicts
- [ ] **Outcome 8**: PortfolioInsight.diversification_score clamped to [0, 1]
- [ ] **Outcome 9**: Both models serialize correctly via model_dump()

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_final_verdict_valid**: Create FinalVerdict with valid data, assert all fields
2. **test_final_verdict_confidence_clamped_high**: overall_confidence=1.5 -> 1.0
3. **test_final_verdict_confidence_clamped_low**: overall_confidence=-0.3 -> 0.0
4. **test_final_verdict_strong_buy_downgrade**: STRONG_BUY + confidence=0.6 -> downgraded to BUY
5. **test_final_verdict_strong_sell_downgrade**: STRONG_SELL + confidence=0.6 -> downgraded to SELL
6. **test_final_verdict_strong_buy_passes**: STRONG_BUY + confidence=0.80 -> stays STRONG_BUY
7. **test_final_verdict_strong_sell_passes**: STRONG_SELL + confidence=0.75 -> stays STRONG_SELL
8. **test_final_verdict_buy_low_confidence_ok**: BUY + confidence=0.3 -> stays BUY (no downgrade for non-STRONG)
9. **test_final_verdict_default_timestamp**: timestamp defaults to datetime
10. **test_final_verdict_serializable**: model_dump() returns dict
11. **test_portfolio_insight_valid**: Create PortfolioInsight with list of FinalVerdicts
12. **test_portfolio_insight_diversification_clamped_high**: diversification_score=1.5 -> 1.0
13. **test_portfolio_insight_diversification_clamped_low**: diversification_score=-0.5 -> 0.0
14. **test_portfolio_insight_serializable**: model_dump() returns dict with nested verdicts
15. **test_final_verdict_signal_literal_validation**: Invalid signal raises ValidationError

### Mocking Strategy
- No external services -- pure Pydantic models, no mocking needed

### Coverage Expectation
- Both models tested for instantiation, clamping, validation rules, and serialization
- Every field_validator and model_validator has at least one edge-case test

---

## References
- roadmap.md (Phase 2, S2.2)
- CLAUDE.md (Data Schemas, Key Rules -- STRONG_BUY/STRONG_SELL requires confidence >= 0.75)
