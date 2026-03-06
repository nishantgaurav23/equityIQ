"""Tests for config/data_contracts.py -- S2.1 + S2.2 Data Contract Schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from config.data_contracts import (
    AnalystReport,
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PortfolioInsight,
    PulseReport,
    RiskGuardianReport,
    ValuationReport,
)

# --- AnalystReport (FR-1) ---


def _base_fields(**overrides):
    defaults = {
        "ticker": "AAPL",
        "agent_name": "test_agent",
        "signal": "BUY",
        "confidence": 0.85,
        "reasoning": "Test reasoning",
    }
    defaults.update(overrides)
    return defaults


class TestAnalystReport:
    def test_valid_creation(self):
        r = AnalystReport(**_base_fields())
        assert r.ticker == "AAPL"
        assert r.agent_name == "test_agent"
        assert r.signal == "BUY"
        assert r.confidence == 0.85
        assert r.reasoning == "Test reasoning"

    def test_confidence_clamped_high(self):
        r = AnalystReport(**_base_fields(confidence=1.5))
        assert r.confidence == 1.0

    def test_confidence_clamped_low(self):
        r = AnalystReport(**_base_fields(confidence=-0.3))
        assert r.confidence == 0.0

    def test_default_timestamp(self):
        r = AnalystReport(**_base_fields())
        assert isinstance(r.timestamp, datetime)

    def test_signal_literal_validation(self):
        with pytest.raises(ValidationError):
            AnalystReport(**_base_fields(signal="STRONG_BUY"))

    def test_serializable(self):
        r = AnalystReport(**_base_fields())
        d = r.model_dump()
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert d["signal"] == "BUY"


# --- ValuationReport (FR-2) ---


class TestValuationReport:
    def test_inherits_analyst_report(self):
        r = ValuationReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_nullable_fields(self):
        r = ValuationReport(**_base_fields())
        assert r.pe_ratio is None
        assert r.pb_ratio is None
        assert r.revenue_growth is None
        assert r.debt_to_equity is None
        assert r.fcf_yield is None
        assert r.intrinsic_value_gap is None

    def test_with_values(self):
        r = ValuationReport(
            **_base_fields(),
            pe_ratio=25.5,
            pb_ratio=3.2,
            revenue_growth=0.15,
            debt_to_equity=0.8,
            fcf_yield=0.04,
            intrinsic_value_gap=-0.12,
        )
        assert r.pe_ratio == 25.5
        assert r.intrinsic_value_gap == -0.12

    def test_serializable(self):
        r = ValuationReport(**_base_fields(), pe_ratio=20.0)
        d = r.model_dump()
        assert d["pe_ratio"] == 20.0


# --- MomentumReport (FR-3) ---


class TestMomentumReport:
    def test_inherits_analyst_report(self):
        r = MomentumReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_rsi_clamped_high(self):
        r = MomentumReport(**_base_fields(), rsi_14=150.0)
        assert r.rsi_14 == 100.0

    def test_rsi_clamped_low(self):
        r = MomentumReport(**_base_fields(), rsi_14=-10.0)
        assert r.rsi_14 == 0.0

    def test_momentum_score_clamped_high(self):
        r = MomentumReport(**_base_fields(), price_momentum_score=2.0)
        assert r.price_momentum_score == 1.0

    def test_momentum_score_clamped_low(self):
        r = MomentumReport(**_base_fields(), price_momentum_score=-2.0)
        assert r.price_momentum_score == -1.0

    def test_nullable_fields(self):
        r = MomentumReport(**_base_fields())
        assert r.rsi_14 is None
        assert r.macd_signal is None
        assert r.above_sma_50 is None
        assert r.above_sma_200 is None
        assert r.volume_trend is None
        assert r.price_momentum_score is None


# --- PulseReport (FR-4) ---


class TestPulseReport:
    def test_inherits_analyst_report(self):
        r = PulseReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_sentiment_clamped_high(self):
        r = PulseReport(**_base_fields(), sentiment_score=5.0)
        assert r.sentiment_score == 1.0

    def test_sentiment_clamped_low(self):
        r = PulseReport(**_base_fields(), sentiment_score=-5.0)
        assert r.sentiment_score == -1.0

    def test_confidence_cap_low_articles(self):
        r = PulseReport(**_base_fields(confidence=0.9), article_count=2)
        assert r.confidence == 0.70

    def test_confidence_ok_enough_articles(self):
        r = PulseReport(**_base_fields(confidence=0.9), article_count=3)
        assert r.confidence == 0.9

    def test_confidence_below_cap_low_articles(self):
        r = PulseReport(**_base_fields(confidence=0.5), article_count=1)
        assert r.confidence == 0.5

    def test_defaults(self):
        r = PulseReport(**_base_fields())
        assert r.article_count == 0
        assert r.top_headlines == []
        assert r.event_flags == []


# --- EconomyReport (FR-5) ---


class TestEconomyReport:
    def test_inherits_analyst_report(self):
        r = EconomyReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_valid_macro_regime(self):
        for regime in ["expansion", "contraction", "stagflation", "recovery"]:
            r = EconomyReport(**_base_fields(), macro_regime=regime)
            assert r.macro_regime == regime

    def test_invalid_macro_regime(self):
        with pytest.raises(ValidationError):
            EconomyReport(**_base_fields(), macro_regime="boom")

    def test_nullable_fields(self):
        r = EconomyReport(**_base_fields())
        assert r.gdp_growth is None
        assert r.inflation_rate is None
        assert r.fed_funds_rate is None
        assert r.unemployment_rate is None
        assert r.macro_regime is None


# --- ComplianceReport (FR-6) ---


class TestComplianceReport:
    def test_inherits_analyst_report(self):
        r = ComplianceReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_risk_score_clamped_high(self):
        r = ComplianceReport(**_base_fields(), risk_score=1.5)
        assert r.risk_score == 1.0

    def test_risk_score_clamped_low(self):
        r = ComplianceReport(**_base_fields(), risk_score=-0.5)
        assert r.risk_score == 0.0

    def test_defaults(self):
        r = ComplianceReport(**_base_fields())
        assert r.risk_flags == []
        assert r.latest_filing_type is None
        assert r.days_since_filing is None
        assert r.risk_score is None


# --- RiskGuardianReport (FR-7) ---


class TestRiskGuardianReport:
    def test_inherits_analyst_report(self):
        r = RiskGuardianReport(**_base_fields())
        assert isinstance(r, AnalystReport)

    def test_position_size_capped(self):
        r = RiskGuardianReport(**_base_fields(), suggested_position_size=0.20)
        assert r.suggested_position_size == 0.10

    def test_position_size_valid(self):
        r = RiskGuardianReport(**_base_fields(), suggested_position_size=0.05)
        assert r.suggested_position_size == 0.05

    def test_volatility_non_negative(self):
        r = RiskGuardianReport(**_base_fields(), annualized_volatility=-0.5)
        assert r.annualized_volatility == 0.0

    def test_max_drawdown_non_positive(self):
        r = RiskGuardianReport(**_base_fields(), max_drawdown=0.5)
        assert r.max_drawdown == 0.0

    def test_max_drawdown_valid(self):
        r = RiskGuardianReport(**_base_fields(), max_drawdown=-0.25)
        assert r.max_drawdown == -0.25

    def test_nullable_fields(self):
        r = RiskGuardianReport(**_base_fields())
        assert r.beta is None
        assert r.annualized_volatility is None
        assert r.sharpe_ratio is None
        assert r.max_drawdown is None
        assert r.suggested_position_size is None
        assert r.var_95 is None


# --- FinalVerdict (S2.2 FR-1) ---


def _verdict_fields(**overrides):
    defaults = {
        "ticker": "AAPL",
        "final_signal": "BUY",
        "overall_confidence": 0.80,
        "price_target": 195.0,
        "analyst_signals": {"valuation_scout": "BUY", "momentum_tracker": "HOLD"},
        "risk_summary": "Moderate risk profile",
        "key_drivers": ["Strong fundamentals", "Positive momentum"],
        "session_id": "sess-001",
    }
    defaults.update(overrides)
    return defaults


class TestFinalVerdict:
    def test_valid_creation(self):
        v = FinalVerdict(**_verdict_fields())
        assert v.ticker == "AAPL"
        assert v.final_signal == "BUY"
        assert v.overall_confidence == 0.80
        assert v.price_target == 195.0
        assert v.analyst_signals == {"valuation_scout": "BUY", "momentum_tracker": "HOLD"}
        assert v.risk_summary == "Moderate risk profile"
        assert v.key_drivers == ["Strong fundamentals", "Positive momentum"]
        assert v.session_id == "sess-001"

    def test_confidence_clamped_high(self):
        v = FinalVerdict(**_verdict_fields(overall_confidence=1.5))
        assert v.overall_confidence == 1.0

    def test_confidence_clamped_low(self):
        v = FinalVerdict(**_verdict_fields(overall_confidence=-0.3))
        assert v.overall_confidence == 0.0

    def test_strong_buy_downgrade(self):
        v = FinalVerdict(**_verdict_fields(final_signal="STRONG_BUY", overall_confidence=0.6))
        assert v.final_signal == "BUY"

    def test_strong_sell_downgrade(self):
        v = FinalVerdict(**_verdict_fields(final_signal="STRONG_SELL", overall_confidence=0.6))
        assert v.final_signal == "SELL"

    def test_strong_buy_passes(self):
        v = FinalVerdict(**_verdict_fields(final_signal="STRONG_BUY", overall_confidence=0.80))
        assert v.final_signal == "STRONG_BUY"

    def test_strong_sell_passes(self):
        v = FinalVerdict(**_verdict_fields(final_signal="STRONG_SELL", overall_confidence=0.75))
        assert v.final_signal == "STRONG_SELL"

    def test_buy_low_confidence_ok(self):
        v = FinalVerdict(**_verdict_fields(final_signal="BUY", overall_confidence=0.3))
        assert v.final_signal == "BUY"
        assert v.overall_confidence == 0.3

    def test_hold_low_confidence_ok(self):
        v = FinalVerdict(**_verdict_fields(final_signal="HOLD", overall_confidence=0.2))
        assert v.final_signal == "HOLD"

    def test_sell_low_confidence_ok(self):
        v = FinalVerdict(**_verdict_fields(final_signal="SELL", overall_confidence=0.4))
        assert v.final_signal == "SELL"

    def test_default_timestamp(self):
        v = FinalVerdict(**_verdict_fields())
        assert isinstance(v.timestamp, datetime)

    def test_serializable(self):
        v = FinalVerdict(**_verdict_fields())
        d = v.model_dump()
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert d["final_signal"] == "BUY"
        assert d["analyst_signals"]["valuation_scout"] == "BUY"

    def test_signal_literal_validation(self):
        with pytest.raises(ValidationError):
            FinalVerdict(**_verdict_fields(final_signal="MAYBE"))

    def test_nullable_price_target(self):
        v = FinalVerdict(**_verdict_fields(price_target=None))
        assert v.price_target is None


# --- PortfolioInsight (S2.2 FR-2) ---


class TestPortfolioInsight:
    def _make_verdict(self, ticker="AAPL", **kw):
        return FinalVerdict(**_verdict_fields(ticker=ticker, **kw))

    def test_valid_creation(self):
        v1 = self._make_verdict("AAPL")
        v2 = self._make_verdict("TSLA")
        p = PortfolioInsight(
            tickers=["AAPL", "TSLA"],
            verdicts=[v1, v2],
            portfolio_signal="BUY",
            diversification_score=0.72,
            top_pick="AAPL",
        )
        assert p.tickers == ["AAPL", "TSLA"]
        assert len(p.verdicts) == 2
        assert p.portfolio_signal == "BUY"
        assert p.diversification_score == 0.72
        assert p.top_pick == "AAPL"

    def test_diversification_clamped_high(self):
        v = self._make_verdict()
        p = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[v],
            portfolio_signal="HOLD",
            diversification_score=1.5,
        )
        assert p.diversification_score == 1.0

    def test_diversification_clamped_low(self):
        v = self._make_verdict()
        p = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[v],
            portfolio_signal="HOLD",
            diversification_score=-0.5,
        )
        assert p.diversification_score == 0.0

    def test_serializable(self):
        v = self._make_verdict()
        p = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[v],
            portfolio_signal="BUY",
            diversification_score=0.6,
            top_pick="AAPL",
        )
        d = p.model_dump()
        assert isinstance(d, dict)
        assert d["tickers"] == ["AAPL"]
        assert len(d["verdicts"]) == 1
        assert d["verdicts"][0]["ticker"] == "AAPL"

    def test_nullable_top_pick(self):
        v = self._make_verdict()
        p = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[v],
            portfolio_signal="HOLD",
            diversification_score=0.5,
            top_pick=None,
        )
        assert p.top_pick is None

    def test_default_timestamp(self):
        v = self._make_verdict()
        p = PortfolioInsight(
            tickers=["AAPL"],
            verdicts=[v],
            portfolio_signal="HOLD",
            diversification_score=0.5,
        )
        assert isinstance(p.timestamp, datetime)

    def test_signal_literal_validation(self):
        v = self._make_verdict()
        with pytest.raises(ValidationError):
            PortfolioInsight(
                tickers=["AAPL"],
                verdicts=[v],
                portfolio_signal="MAYBE",
                diversification_score=0.5,
            )
