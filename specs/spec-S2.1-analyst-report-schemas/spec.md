# Spec S2.1 -- Analyst Report Schemas

## Overview
Define the base `AnalystReport` Pydantic v2 model and 6 specialist subclasses used as the output schema for each analyst agent. All schemas enforce field validation with clamping (confidence [0,1], momentum [-1,1], position size capped at 0.10). These are the core data contracts for the entire agent system.

## Dependencies
- S1.1 (dependency-declaration) -- Pydantic v2 must be available

## Target Location
- `config/data_contracts.py`

---

## Functional Requirements

### FR-1: Base AnalystReport model
- **What**: Pydantic BaseModel with common fields shared by all analyst agents
- **Fields**:
  - `ticker: str` -- stock symbol (uppercase, 1-5 chars)
  - `agent_name: str` -- name of the producing agent
  - `signal: Literal["BUY", "HOLD", "SELL"]` -- directional signal
  - `confidence: float` -- clamped to [0.0, 1.0] via field_validator
  - `reasoning: str` -- explanation of the signal
  - `timestamp: datetime` -- defaults to utcnow
- **Edge cases**: confidence < 0 clamped to 0, confidence > 1 clamped to 1

### FR-2: ValuationReport subclass
- **What**: Extends AnalystReport with fundamental valuation metrics
- **Fields**:
  - `pe_ratio: float | None` -- price-to-earnings ratio
  - `pb_ratio: float | None` -- price-to-book ratio
  - `revenue_growth: float | None` -- YoY revenue growth rate
  - `debt_to_equity: float | None` -- debt/equity ratio
  - `fcf_yield: float | None` -- free cash flow yield
  - `intrinsic_value_gap: float | None` -- % gap between intrinsic and market price
- **Edge cases**: All financial fields nullable (data may be unavailable)

### FR-3: MomentumReport subclass
- **What**: Extends AnalystReport with technical analysis indicators
- **Fields**:
  - `rsi_14: float | None` -- 14-day RSI, clamped [0, 100]
  - `macd_signal: float | None` -- MACD signal line value
  - `above_sma_50: bool | None` -- price above 50-day SMA
  - `above_sma_200: bool | None` -- price above 200-day SMA
  - `volume_trend: str | None` -- e.g. "increasing", "decreasing", "stable"
  - `price_momentum_score: float | None` -- clamped [-1.0, 1.0]
- **Edge cases**: rsi_14 clamped [0, 100], price_momentum_score clamped [-1, 1]

### FR-4: PulseReport subclass
- **What**: Extends AnalystReport with news sentiment data
- **Fields**:
  - `sentiment_score: float | None` -- clamped [-1.0, 1.0]
  - `article_count: int` -- number of articles analyzed (default 0)
  - `top_headlines: list[str]` -- up to 5 headlines (default empty list)
  - `event_flags: list[str]` -- detected events like "earnings", "merger" (default empty list)
- **Edge cases**: sentiment_score clamped [-1, 1]. Confidence must not exceed 0.70 if article_count < 3

### FR-5: EconomyReport subclass
- **What**: Extends AnalystReport with macroeconomic indicators
- **Fields**:
  - `gdp_growth: float | None` -- GDP growth rate
  - `inflation_rate: float | None` -- current inflation rate
  - `fed_funds_rate: float | None` -- Federal funds rate
  - `unemployment_rate: float | None` -- unemployment rate
  - `macro_regime: Literal["expansion", "contraction", "stagflation", "recovery"] | None`
- **Edge cases**: All fields nullable (FRED data may be unavailable)

### FR-6: ComplianceReport subclass
- **What**: Extends AnalystReport with SEC filing and regulatory risk data
- **Fields**:
  - `latest_filing_type: str | None` -- e.g. "10-K", "10-Q", "8-K"
  - `days_since_filing: int | None` -- days since most recent filing
  - `risk_flags: list[str]` -- flags like "going_concern", "restatement", "late_filing" (default empty list)
  - `risk_score: float | None` -- clamped [0.0, 1.0]
- **Edge cases**: risk_score clamped [0, 1]. If "going_concern" or "restatement" in risk_flags, signal must be SELL

### FR-7: RiskGuardianReport subclass
- **What**: Extends AnalystReport with portfolio risk metrics
- **Fields**:
  - `beta: float | None` -- market beta
  - `annualized_volatility: float | None` -- annualized vol (non-negative)
  - `sharpe_ratio: float | None` -- risk-adjusted return
  - `max_drawdown: float | None` -- maximum drawdown (non-positive)
  - `suggested_position_size: float | None` -- clamped [0.0, 0.10] (10% max)
  - `var_95: float | None` -- 95% Value at Risk
- **Edge cases**: suggested_position_size capped at 0.10. annualized_volatility clamped >= 0. max_drawdown clamped <= 0

---

## Tangible Outcomes

- [ ] **Outcome 1**: `config/data_contracts.py` exists and is importable
- [ ] **Outcome 2**: All 7 models (AnalystReport + 6 subclasses) can be instantiated with valid data
- [ ] **Outcome 3**: field_validators clamp confidence to [0, 1] (values outside range are clamped, not rejected)
- [ ] **Outcome 4**: field_validators clamp rsi_14 [0, 100], price_momentum_score [-1, 1], sentiment_score [-1, 1], risk_score [0, 1]
- [ ] **Outcome 5**: suggested_position_size is capped at 0.10 via field_validator
- [ ] **Outcome 6**: PulseReport confidence capped at 0.70 when article_count < 3
- [ ] **Outcome 7**: All subclasses inherit from AnalystReport (isinstance check passes)
- [ ] **Outcome 8**: Models serialize to dict/JSON correctly via model_dump()

---

## Test-Driven Requirements

### Tests to Write First (Red -> Green)
1. **test_analyst_report_valid**: Create AnalystReport with valid data, assert all fields correct
2. **test_analyst_report_confidence_clamped_high**: confidence=1.5 -> clamped to 1.0
3. **test_analyst_report_confidence_clamped_low**: confidence=-0.3 -> clamped to 0.0
4. **test_analyst_report_default_timestamp**: timestamp defaults to a datetime
5. **test_valuation_report_inherits**: ValuationReport is instance of AnalystReport
6. **test_valuation_report_nullable_fields**: All financial fields accept None
7. **test_momentum_report_rsi_clamped**: rsi_14=150 -> clamped to 100
8. **test_momentum_report_momentum_score_clamped**: price_momentum_score=2.0 -> clamped to 1.0, -2.0 -> -1.0
9. **test_pulse_report_sentiment_clamped**: sentiment_score=5.0 -> clamped to 1.0
10. **test_pulse_report_confidence_cap_low_articles**: article_count=2 + confidence=0.9 -> confidence capped at 0.70
11. **test_pulse_report_confidence_ok_enough_articles**: article_count=3 + confidence=0.9 -> stays 0.9
12. **test_economy_report_macro_regime_literal**: valid regime values accepted, invalid rejected
13. **test_compliance_report_risk_score_clamped**: risk_score=1.5 -> clamped to 1.0
14. **test_risk_guardian_position_size_capped**: suggested_position_size=0.20 -> capped to 0.10
15. **test_risk_guardian_volatility_non_negative**: annualized_volatility=-0.5 -> clamped to 0.0
16. **test_risk_guardian_max_drawdown_non_positive**: max_drawdown=0.5 -> clamped to 0.0
17. **test_all_models_serializable**: Each model's model_dump() returns a dict
18. **test_signal_literal_validation**: Invalid signal value raises ValidationError

### Mocking Strategy
- No external services -- pure Pydantic models, no mocking needed

### Coverage Expectation
- All 7 models tested for instantiation, clamping, inheritance, and serialization
- Every field_validator has at least one edge-case test

---

## References
- roadmap.md (Phase 2, S2.1)
- design.md (Data Schemas section)
- CLAUDE.md (Data Schemas, Key Rules)
