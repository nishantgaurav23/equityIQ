"""Data contracts for EquityIQ analyst agents -- Pydantic v2 schemas."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _utcnow():
    return datetime.now(timezone.utc)


class AnalystReport(BaseModel):
    """Base report schema shared by all analyst agents."""

    ticker: str
    agent_name: str
    signal: Literal["BUY", "HOLD", "SELL"]
    confidence: float
    reasoning: str
    timestamp: datetime = Field(default_factory=_utcnow)

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))


class ValuationReport(AnalystReport):
    """Fundamental valuation metrics."""

    pe_ratio: float | None = None
    pb_ratio: float | None = None
    revenue_growth: float | None = None
    debt_to_equity: float | None = None
    fcf_yield: float | None = None
    intrinsic_value_gap: float | None = None


class MomentumReport(AnalystReport):
    """Technical analysis indicators."""

    rsi_14: float | None = None
    macd_signal: float | None = None
    above_sma_50: bool | None = None
    above_sma_200: bool | None = None
    volume_trend: str | None = None
    price_momentum_score: float | None = None

    @field_validator("rsi_14", mode="before")
    @classmethod
    def clamp_rsi(cls, v):
        if v is None:
            return v
        return max(0.0, min(100.0, float(v)))

    @field_validator("price_momentum_score", mode="before")
    @classmethod
    def clamp_momentum(cls, v):
        if v is None:
            return v
        return max(-1.0, min(1.0, float(v)))


class PulseReport(AnalystReport):
    """News sentiment and event data."""

    sentiment_score: float | None = None
    article_count: int = 0
    top_headlines: list[str] = []
    event_flags: list[str] = []

    @field_validator("sentiment_score", mode="before")
    @classmethod
    def clamp_sentiment(cls, v):
        if v is None:
            return v
        return max(-1.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def cap_confidence_low_articles(self):
        if self.article_count < 3 and self.confidence > 0.70:
            self.confidence = 0.70
        return self


class EconomyReport(AnalystReport):
    """Macroeconomic indicators."""

    gdp_growth: float | None = None
    inflation_rate: float | None = None
    fed_funds_rate: float | None = None
    unemployment_rate: float | None = None
    macro_regime: Literal["expansion", "contraction", "stagflation", "recovery"] | None = None


class ComplianceReport(AnalystReport):
    """SEC filing and regulatory risk data."""

    latest_filing_type: str | None = None
    days_since_filing: int | None = None
    risk_flags: list[str] = []
    risk_score: float | None = None

    @field_validator("risk_score", mode="before")
    @classmethod
    def clamp_risk_score(cls, v):
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))


class RiskGuardianReport(AnalystReport):
    """Portfolio risk metrics."""

    beta: float | None = None
    annualized_volatility: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    suggested_position_size: float | None = None
    var_95: float | None = None

    @field_validator("suggested_position_size", mode="before")
    @classmethod
    def cap_position_size(cls, v):
        if v is None:
            return v
        return max(0.0, min(0.10, float(v)))

    @field_validator("annualized_volatility", mode="before")
    @classmethod
    def clamp_volatility(cls, v):
        if v is None:
            return v
        return max(0.0, float(v))

    @field_validator("max_drawdown", mode="before")
    @classmethod
    def clamp_drawdown(cls, v):
        if v is None:
            return v
        return min(0.0, float(v))


class FinalVerdict(BaseModel):
    """Synthesized output of all analyst agents -- 5-level signal."""

    ticker: str
    final_signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    overall_confidence: float
    price_target: float | None = None
    analyst_signals: dict[str, str] = {}
    risk_summary: str = ""
    key_drivers: list[str] = []
    session_id: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v):
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def enforce_strong_signal_threshold(self):
        if self.final_signal == "STRONG_BUY" and self.overall_confidence < 0.75:
            self.final_signal = "BUY"
        elif self.final_signal == "STRONG_SELL" and self.overall_confidence < 0.75:
            self.final_signal = "SELL"
        return self


class PortfolioInsight(BaseModel):
    """Aggregated analysis across multiple stocks."""

    tickers: list[str]
    verdicts: list[FinalVerdict]
    portfolio_signal: Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
    diversification_score: float
    top_pick: str | None = None
    timestamp: datetime = Field(default_factory=_utcnow)

    @field_validator("diversification_score", mode="before")
    @classmethod
    def clamp_diversification(cls, v):
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))
