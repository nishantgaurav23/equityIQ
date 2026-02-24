"""
What it does:
    This file defines all the data shapes (schemas) for EquityIQ. Every piece of data flowing between agents - 
    from raw analyst output to final verdict - must match a schema defined here.

    Think of it as a contract: "If yoy're a Valuation Scout, your output must look exactly like this. If you're
    the Signal Synthesizer, your input will always look like this.

Why It's Needed:
    Without schemas chaos:
        - Agent A returns {"signal": "buy"}, Agent B returns {"recommendation"" "BUY"}, Agent C returns {"action": 1}
          - the synthesizer has no idea what to expect
        - Runtime errors are hard to debug ("I got a string but expected a float somewhere")
        - No IDE autocomplete, no type hints, no validation

    With pydantic schemas:
        - Every filed is typed, validated, and documented.
        - Bad data is caught at the boundary (before it enters your system)
        - Every agent knows exactly what shape it outputs should be 

---
How it helps the rest of the project

    - tools/*py uses ValutaionMetrics, TechnicalMetrics etc, to structure fetched data
    - agents/*py retturns typed AnalystReport subclasses
    - models/signal_fusion.py receives a List[AnalystReport] and returns FinalVerdict
    - memory/insight_vault.py stores and retrives FinalVerdict objects
    - FastAPI in app.py uses these as request/response models automatically

---
Concepts to Know:
    - Pydantic v2 - from pydantic import BaseModel, Field, field_validator
    - Filed(defaults=..., ge=0.0, le=1.0, description="...") - built-in range validation
    - @filed_validator("field_name") - cusotm validation logic
    - model_config = ConfigDict(...) - Pydantic v2 way to configure a model
    - Literal["BUY", "HOLD", "SELL"] - restricts a string to specific values
    - Optional[float] - filed can be None if data unavailable

---
Classes to Define(in order)

config/
└── data_contracts.py
    ├── class AnalystReport        ← Base class all analyst reports inherit from
    ├── class ValuationReport      ← Output of valuation_scout.py
    ├── class MomentumReport       ← Output of momentum_tracker.py
    ├── class PulseReport          ← Output of pulse_monitor.py
    ├── class EconomyReport        ← Output of economy_watcher.py
    ├── class ComplianceReport     ← Output of compliance_checker.py
    ├── class RiskGuardianReport   ← Output of risk_guardian.py
    ├── class FinalVerdict         ← Output of signal_synthesizer.py
    └── class PortfolioInsight     ← Output of market_conductor.py (multi-stock)

---
Key difference from analyst reports:
    - Field(...) means required — caller must pass it
    - Field(default=None) means optional — safe to skip
    - Field(default_factory=datetime.utcnow) means auto-generated — never pass manually
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict

class AnalystReport(BaseModel):
    """Base schema that every specialist agent's output must confirm to."""

    model_config = ConfigDict(extra="allow")

    ticker: str = Field(..., description="Stock ticker symbol e.g. AAPL")
    agent_name: str = Field(..., description="Name of the agent producing this report")
    signal: Literal["BUY", "HOLD", "SELL"] = Field(..., description="Agent's directional call")
    confidence: float = Field(..., description="Confidence in the signal, clamed to [0.0, 1.0]")
    rationale: str = Field(..., description="1-2 sentence explaination of the signal")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    horizon: str = Field(default="1M", description="Investement horizon: 1W, 1M, 3M, 1Y")

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v) -> float:
        """Clamp to [0, 1] instead of raising - agents sometimes returns 1.05."""
        return max(0.0, min(1.0, float(v)))
    
    @field_validator("ticker", mode="before")
    @classmethod
    def uppercase_ticker(cls, v) -> str:
        return str(v).upper().strip()

    

class ValuationReport(AnalystReport):
    """Output schema for valuation_scout.py - fundamental fiancial metrics."""
    agent_name: str = Field(default="ValuationScout")

    pe_ratio: Optional[float] = Field(default=None, description="Price-to-Earnings ratio")
    pb_ratio: Optional[float] = Field(default=None, description="Price-to-Book ratio")
    revenue_growth: Optional[float] = Field(default=None, description="YoY revenue growth rate")
    debt_to_equity: Optional[float] = Field(default=None, description="Debt-to-Equity ratio")
    fcf_yield: Optional[float] = Field(default=None, description="Free Cash Flow Yield")
    intrinsic_value_gap: Optional[float] = Field(
        default=None,
        description="% above (+) or below (-) estimated fait value"
    )
class MomentumReport(AnalystReport):
    """Extra fields form techinal_engine.py"""
    agent_name: str = Field(default="MomentumTracker")

    rsi_14: Optional[float] = Field(default=None, description=" RSI 14 day: 0-100, <30 oversold, >70 overbought (Relative Strength Index (14-day)) ")
    macd_signal: Optional[str] = Field(default=None, description="MACD crossover: bullish_cross | bearish_cross | neutral")
    above_sma_50: Optional[bool] = Field(default=None, description="True if price is above 50-day simple moving average")
    above_sma_200: Optional[bool] = Field(default=None, description="True if price is above 200-day simple moving average")
    volume_trend: Optional[str] = Field(default=None, description="Recent volume direction: increasing | decreasing | flat")
    price_momentum_score: Optional[float] = Field(default=None, description="Composite momentum score: -1.0 strong down to +1.0 strong up")

    @field_validator("price_momentum_score", mode="before")
    @classmethod
    def clamp_momentum(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(-1.0, min(1.0, float(v)))


class PulseReport(AnalystReport):
    """
    Extra fields from news_connector.py:
        - sentiment_score: Optional[float]  ← hint: [-1.0 negative, +1.0 positive]
        - article_count: Optional[int]
        - top_headlines: Optional[list[str]]  ← top 3 headlines
        - event_flags: Optional[list[str]]   ← ["earnings_beat", "lawsuit", "product_launch"]
    """

    agent_name : str = Field(default="PulseMonitor")

    sentiment_score: Optional[float] = Field(default=None, description="Aggregate news sentiment: -1.0 very negative to +1-.0 very positive")
    article_count: Optional[int] = Field(default=None, description="Number of news article analyzed in the lookback window")
    top_headlines: Optional[list[str]] = Field(default=None, description="Top 3 most relevant headlines for this ticker")
    event_flags: Optional[list[str]] = Field(default=None, description="detected market events: earnings_beat | earnings_miss | lawsuit | product_launch | insider_trade | downgrade | upgrade")

    @field_validator("sentiment_score", mode="before")
    @classmethod
    def clamp_sentiments(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(-1.0, min(1.0, float(v)))
    
class EconomyReport(AnalystReport):
    """
      Extra fields from fred_connector.py:
        - gdp_growth: Optional[float]
        - inflation_rate: Optional[float]
        - fed_funds_rate: Optional[float]
        - unemployment_rate: Optional[float]
        - macro_regime: Optional[str]      ← "expansion", "contraction", "stagflation", "recovery"
    """
    agent_name: str = Field(default="EconomyWatcher")

    gdp_growth: Optional[float] = Field(default=None, description="Latest GDP growth from fred : Typically -5.0 to +10.0, expressed as percentage")
    inflation_rate: Optional[float] = Field(default=None, description="Current CPI inflation rate: Typically 0.0 to 15.0, expressed as percentage")
    fed_funds_rate: Optional[float] = Field(default=None, description="Current Fedral Reserve benchmark interest rate: Typically 0.0 to 20.0, expressed as percentage")
    unemployment_rate: Optional[float] = Field(default=None, description="Current US unemployment rate from FRED: Typically 2.0 to 15.0, expressed as percentage")
    macro_regime: Optional[str] = Field(default=None, description="Current macroeconomic environment: expansion | contraction | stagflation | recovery")


class ComplianceReport(AnalystReport):
    """
    Extra fields from sec_connector.py:
        - latest_filing_type: Optional[str]   ← "10-K", "10-Q", "8-K"
        - days_since_filing: Optional[int]
        - risk_flags: Optional[list[str]]     ← ["going_concern", "restatement", "investigation"]
        - risk_score: Optional[float]         ← hint: 0.0 = clean, 1.0 = high risk
    """
    agent_name: str = Field(default="ComplianceChecker")

    latest_filing_type: Optional[str] = Field(default=None, description="Recent SEC filing: 10-K | 10-Q | 8-K | DEF 14A | S-1")
    days_since_filing: Optional[int] = Field(default=None, description="Number of days since the most recent SEC filing")
    risk_flags: Optional[list[str]] = Field(default=None, description="Regulatory red flags detected in SEC filings: going_concern | restatement | investigation | insider_selling | late_filing")
    risk_score: Optional[float] = Field(default=None, description="Composite regulatory risk score derived from filings: 0.0 (clean, no flags) to 1.0 (high risk, multiple flags)")

    @field_validator("risk_score", mode="before")
    @classmethod
    def clamp_risk(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(0.0, min(1.0, float(v)))

class RiskGuardianReport(AnalystReport):
    """
    Extra fields from risk_calculator.py:
        - beta: Optional[float]               ← market sensitivity
        - annualized_volatility: Optional[float]
        - sharpe_ratio: Optional[float]
        - max_drawdown: Optional[float]
        - suggested_position_size: Optional[float]  ← % of portfolio (0.0 to 1.0)
        - var_95: Optional[float]             ← Value at Risk at 95% confidence
    """
    agent_name: str = Field(default="RiskGuardian")

    beta: Optional[float] = Field(default=None, description="Stock's sensitivity to overall market movement: <1.0 less volatile than market, > 1.0 more volatile, 1.0 = moves with market")
    annualized_volatility: Optional[float] = Field(default=None, description="Annualized standard deviations of daily returns: 0.0 to 1.0+, expressed as decimal e.g 0.25 = 25% volatility")
    sharpe_ratio: Optional[float] = Field(default=None, description="Risk adjusted return - return per unit of risk taken: <0 bad, 0-1 acceptable, 1-2 good, >2 excellent")
    max_drawdown: Optional[float] = Field(default=None, description="Largest peak-to-trough price decline in the lookback period: -1.0 (100% loss) to 0.0 (no drawdown), e.g. -0.35 = 35% drop")
    suggested_position_size: Optional[float] = Field(default=None, description="Recommended portfolio allocation for a particular stock: 0.0 (do not hold) to 1.0 (100% allocation), typically 0.02 to 0.10")
    var_95: Optional[float] = Field(default=None, description="Value at Risk - max accepted loss at 95% confidence over 1 day: Negative float e.g. -0.03 means 3% max daily loss at 95% confidence")

    @field_validator("suggested_position_size", mode="before")
    @classmethod
    def clamp_position_size(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(0.0, min(1.0, float(v)))
    
    @field_validator("max_drawdown", mode="before")
    @classmethod
    def clamp_drawdown(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(-1.0, min(0.0, float(v)))


class FinalVerdict(BaseModel):
    """
    Inherits from: BaseModel (not AnalystReport)                                                                                
    Reason: This is not an analyst — it is the synthesized output of all analysts 
    Fields:
        - ticker: str
        - final_signal: Literal["STRONG_BUY","BUY","HOLD","SELL","STRONG_SELL"]
        - overall_confidence: float       ← hint: weighted average of all agent confidences
        - price_target: Optional[float]
        - horizon: str
        - analyst_signals: list[AnalystReport]  ← all 6 reports (excl. risk)
        - risk_summary: Optional[RiskGuardianReport]
        - key_drivers: list[str]          ← top 3 reasons for the verdict
        - created_at: datetime
        - session_id: str                 ← for memory lookup later
    """
    ticker: str = Field(..., description="Stock ticker this verdict if for e.g. APPL")
    final_signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"] = Field(..., description="Final synthesized recommendation from XGBoost signal fusion")
    overall_confidence: float = Field(..., description="Weighted average confidence across all analyst reports: 0.0 to 1.0")
    price_target: Optional[float] = Field(default=None, description="Estimated 12 month price target in USD")
    horizon: str = Field(default="1M", description="Investment horizon: 1W | 1M | 3M | 1Y")
    analyst_signals: list[AnalystReport] = Field(..., description="All 5 specialist analyst reports that fed into the verdict")
    risk_summary: Optional[RiskGuardianReport] = Field(default=None, description="Risk Guardian assessment, None if agent unavailable")
    key_drivers: list[str] = Field(..., description="Top 3 reasons behind the final signal in plain English")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when verdict was generated")
    session_id: str = Field(..., description="UUID linking this verdict to a memory session in Insight Vault")


class PortfolioInsight(BaseModel):
    """
    Inherits from: BaseModel (not AnalystReport)                                                                                
    Reason: This is not a single stock report — it is a multi-stock portfolio summary  
    Fields:
        - tickers: list[str]
        - verdicts: list[FinalVerdict]
        - portfolio_signal: Literal["OVERWEIGHT","NEUTRAL","UNDERWEIGHT"]
        - diversification_score: Optional[float]
        - top_pick: Optional[str]         ← ticker with strongest signal
        - created_at: datetime
    """
    tickers: list[str] = Field(..., description="List of stock tickers analyzed in this portfolio run e.g ['AAPL','GOOGL','MSFT']")
    verdicts: list[FinalVerdict] = Field(..., description="FinalVerdict for each ticker in the portfolio : Same length as ticker list")
    portfolio_signal: Literal["OVERWEIGHT", "NEUTRAL", "UNDERWEIGHT"] = Field(..., description="Overall portfolio stance based on aggregated verdicts: OVERWEIGHT = mostly BUY singnals, UNDERWEIGHT = mostly SELL signals")
    diversification_score: Optional[float] = Field(default=None, description="How well spread the portfolio is across sectors and risk levels: 0.0 (highly concentrated) to 1.0 (well diversified)")
    top_pick: Optional[str] = Field(default=None, description="Ticker with the strongest BUY signal in the portfolio: Single Ticker string e.g 'AAPL', None if no clear winner")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when this portfolio insight was generated: Auto-set, do not pass manually")

    @field_validator("diversification_score", mode="before")
    @classmethod
    def clamp_diversification(cls, v) -> Optional[float]:
        if v is None:
            return None
        return max(0.0, min(1.0, float(v)))
    
