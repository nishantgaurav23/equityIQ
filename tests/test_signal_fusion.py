"""Tests for models/signal_fusion.py -- XGBoost signal synthesis."""

import pytest

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PulseReport,
    ValuationReport,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def valuation_report():
    return ValuationReport(
        ticker="AAPL",
        agent_name="ValuationScout",
        signal="BUY",
        confidence=0.85,
        reasoning="Undervalued",
        pe_ratio=22.5,
        pb_ratio=8.1,
        revenue_growth=0.12,
        debt_to_equity=1.5,
        fcf_yield=0.04,
        intrinsic_value_gap=0.15,
    )


@pytest.fixture
def momentum_report():
    return MomentumReport(
        ticker="AAPL",
        agent_name="MomentumTracker",
        signal="BUY",
        confidence=0.72,
        reasoning="Strong uptrend",
        rsi_14=62.0,
        macd_signal=1.5,
        above_sma_50=True,
        above_sma_200=True,
        volume_trend="increasing",
        price_momentum_score=0.6,
    )


@pytest.fixture
def pulse_report():
    return PulseReport(
        ticker="AAPL",
        agent_name="PulseMonitor",
        signal="BUY",
        confidence=0.65,
        reasoning="Positive sentiment",
        sentiment_score=0.4,
        article_count=5,
        top_headlines=["Apple beats earnings"],
        event_flags=[],
    )


@pytest.fixture
def economy_report():
    return EconomyReport(
        ticker="AAPL",
        agent_name="EconomyWatcher",
        signal="HOLD",
        confidence=0.60,
        reasoning="Mixed macro",
        gdp_growth=2.1,
        inflation_rate=3.2,
        fed_funds_rate=5.25,
        unemployment_rate=3.7,
        macro_regime="expansion",
    )


@pytest.fixture
def compliance_report():
    return ComplianceReport(
        ticker="AAPL",
        agent_name="ComplianceChecker",
        signal="BUY",
        confidence=0.90,
        reasoning="Clean filings",
        latest_filing_type="10-K",
        days_since_filing=30,
        risk_flags=[],
        risk_score=0.1,
    )


@pytest.fixture
def all_reports(valuation_report, momentum_report, pulse_report, economy_report, compliance_report):
    return [valuation_report, momentum_report, pulse_report, economy_report, compliance_report]


@pytest.fixture
def compliance_going_concern():
    return ComplianceReport(
        ticker="BADCO",
        agent_name="ComplianceChecker",
        signal="SELL",
        confidence=0.95,
        reasoning="Going concern flag",
        latest_filing_type="10-K",
        days_since_filing=10,
        risk_flags=["going_concern"],
        risk_score=0.9,
    )


@pytest.fixture
def compliance_restatement():
    return ComplianceReport(
        ticker="BADCO",
        agent_name="ComplianceChecker",
        signal="SELL",
        confidence=0.88,
        reasoning="Restatement detected",
        latest_filing_type="10-K/A",
        days_since_filing=5,
        risk_flags=["restatement"],
        risk_score=0.85,
    )


# ---------------------------------------------------------------------------
# FR-2: Signal Encoding/Decoding
# ---------------------------------------------------------------------------


class TestSignalEncoding:
    def test_signal_to_numeric_buy(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.signal_to_numeric("BUY") == 1.0

    def test_signal_to_numeric_hold(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.signal_to_numeric("HOLD") == 0.0

    def test_signal_to_numeric_sell(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.signal_to_numeric("SELL") == -1.0

    def test_numeric_to_signal_strong_buy(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.numeric_to_signal(0.5, 0.80) == "STRONG_BUY"

    def test_numeric_to_signal_buy(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.numeric_to_signal(0.5, 0.60) == "BUY"

    def test_numeric_to_signal_hold(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.numeric_to_signal(0.1, 0.60) == "HOLD"

    def test_numeric_to_signal_sell(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.numeric_to_signal(-0.5, 0.60) == "SELL"

    def test_numeric_to_signal_strong_sell(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.numeric_to_signal(-0.5, 0.80) == "STRONG_SELL"


# ---------------------------------------------------------------------------
# FR-1: Feature Extraction
# ---------------------------------------------------------------------------


class TestFeatureExtraction:
    def test_extract_features_single_valuation(self, valuation_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([valuation_report])
        assert features["valuation_signal"] == 1.0
        assert features["valuation_confidence"] == 0.85
        assert features["valuation_pe_ratio"] == 22.5
        assert features["valuation_pb_ratio"] == 8.1
        assert features["valuation_missing"] == 0.0
        # Other agents should be missing
        assert features["momentum_missing"] == 1.0
        assert features["pulse_missing"] == 1.0
        assert features["economy_missing"] == 1.0
        assert features["compliance_missing"] == 1.0

    def test_extract_features_all_reports(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features(all_reports)
        assert features["valuation_missing"] == 0.0
        assert features["momentum_missing"] == 0.0
        assert features["pulse_missing"] == 0.0
        assert features["economy_missing"] == 0.0
        assert features["compliance_missing"] == 0.0
        assert features["momentum_rsi_14"] == 62.0
        assert features["pulse_sentiment_score"] == 0.4
        assert features["economy_gdp_growth"] == 2.1
        assert features["compliance_risk_score"] == 0.1

    def test_extract_features_missing_reports(self, valuation_report, momentum_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([valuation_report, momentum_report])
        assert features["valuation_missing"] == 0.0
        assert features["momentum_missing"] == 0.0
        assert features["pulse_missing"] == 1.0
        assert features["economy_missing"] == 1.0
        assert features["compliance_missing"] == 1.0

    def test_extract_features_none_fields(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        report = ValuationReport(
            ticker="AAPL",
            agent_name="ValuationScout",
            signal="HOLD",
            confidence=0.5,
            reasoning="Uncertain",
            pe_ratio=None,
            pb_ratio=None,
        )
        features = model.extract_features([report])
        assert features["valuation_pe_ratio"] == 0.0
        assert features["valuation_pb_ratio"] == 0.0

    def test_extract_features_empty(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([])
        assert features["valuation_missing"] == 1.0
        assert features["momentum_missing"] == 1.0
        assert features["pulse_missing"] == 1.0
        assert features["economy_missing"] == 1.0
        assert features["compliance_missing"] == 1.0

    def test_extract_features_economy_regime_numeric(self, economy_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([economy_report])
        assert features["economy_macro_regime_numeric"] == 1.0  # expansion

    def test_extract_features_compliance_flags(self, compliance_going_concern):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([compliance_going_concern])
        assert features["compliance_has_going_concern"] == 1.0
        assert features["compliance_has_restatement"] == 0.0

    def test_extract_features_momentum_sma_bools(self, momentum_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        features = model.extract_features([momentum_report])
        assert features["momentum_above_sma_50"] == 1.0
        assert features["momentum_above_sma_200"] == 1.0


# ---------------------------------------------------------------------------
# FR-3: Weighted Average Fallback
# ---------------------------------------------------------------------------


class TestWeightedAverage:
    def test_weighted_average_all_buy(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        # Set all signals to BUY
        for r in all_reports:
            r.signal = "BUY"
            r.confidence = 0.80
        signal, conf = model.weighted_average_predict(all_reports)
        assert signal in ("BUY", "STRONG_BUY")
        assert conf > 0.5

    def test_weighted_average_all_sell(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        for r in all_reports:
            r.signal = "SELL"
            r.confidence = 0.80
        signal, conf = model.weighted_average_predict(all_reports)
        assert signal in ("SELL", "STRONG_SELL")
        assert conf > 0.5

    def test_weighted_average_mixed(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        # Leave as-is (mostly BUY with one HOLD)
        signal, conf = model.weighted_average_predict(all_reports)
        assert signal in ("BUY", "STRONG_BUY", "HOLD")
        assert 0.0 < conf <= 1.0

    def test_weighted_average_missing_agents(self, valuation_report, momentum_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        _, full_conf = model.weighted_average_predict(
            [
                valuation_report,
                momentum_report,
                PulseReport(
                    ticker="AAPL",
                    agent_name="PulseMonitor",
                    signal="BUY",
                    confidence=0.8,
                    reasoning="ok",
                    article_count=5,
                ),
                EconomyReport(
                    ticker="AAPL",
                    agent_name="EconomyWatcher",
                    signal="BUY",
                    confidence=0.8,
                    reasoning="ok",
                ),
                ComplianceReport(
                    ticker="AAPL",
                    agent_name="ComplianceChecker",
                    signal="BUY",
                    confidence=0.8,
                    reasoning="ok",
                ),
            ]
        )
        _, partial_conf = model.weighted_average_predict([valuation_report, momentum_report])
        # Missing 3 agents should reduce confidence
        assert partial_conf < full_conf

    def test_weighted_average_empty(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        signal, conf = model.weighted_average_predict([])
        assert signal == "HOLD"
        assert conf == 0.0


# ---------------------------------------------------------------------------
# FR-4: XGBoost Training
# ---------------------------------------------------------------------------


class TestFit:
    def test_fit_trains_model(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        # Create small training set
        training_data = []
        for _ in range(20):
            training_data.append((all_reports, "BUY"))
        # Add some SELL and HOLD samples
        sell_reports = [r.model_copy() for r in all_reports]
        for r in sell_reports:
            r.signal = "SELL"
            r.confidence = 0.7
        for _ in range(10):
            training_data.append((sell_reports, "SELL"))
        hold_reports = [r.model_copy() for r in all_reports]
        for r in hold_reports:
            r.signal = "HOLD"
            r.confidence = 0.5
        for _ in range(10):
            training_data.append((hold_reports, "HOLD"))

        model.fit(training_data)
        assert model.is_trained is True

    def test_fit_empty_data(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        with pytest.raises(ValueError):
            model.fit([])


# ---------------------------------------------------------------------------
# FR-5: Prediction
# ---------------------------------------------------------------------------


class TestPredict:
    def test_predict_with_trained_model(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        # Train first
        training_data = []
        for _ in range(20):
            training_data.append((all_reports, "BUY"))
        sell_reports = [r.model_copy() for r in all_reports]
        for r in sell_reports:
            r.signal = "SELL"
            r.confidence = 0.7
        for _ in range(10):
            training_data.append((sell_reports, "SELL"))
        hold_reports = [r.model_copy() for r in all_reports]
        for r in hold_reports:
            r.signal = "HOLD"
            r.confidence = 0.5
        for _ in range(10):
            training_data.append((hold_reports, "HOLD"))
        model.fit(training_data)

        verdict = model.predict(all_reports)
        assert isinstance(verdict, FinalVerdict)
        assert verdict.final_signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
        assert 0.0 <= verdict.overall_confidence <= 1.0

    def test_predict_without_model(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        assert model.is_trained is False
        verdict = model.predict(all_reports)
        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"

    def test_predict_returns_final_verdict(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        assert isinstance(verdict, FinalVerdict)
        assert verdict.ticker == "AAPL"
        assert verdict.session_id != ""
        assert len(verdict.analyst_signals) > 0
        assert len(verdict.key_drivers) > 0

    def test_predict_empty_reports(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict([])
        assert verdict.final_signal == "HOLD"
        assert verdict.overall_confidence == 0.0

    def test_predict_populates_all_verdict_fields(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        assert verdict.ticker != ""
        assert verdict.session_id != ""
        assert isinstance(verdict.analyst_signals, dict)
        assert isinstance(verdict.key_drivers, list)
        assert verdict.final_signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")


# ---------------------------------------------------------------------------
# FR-6: Compliance Hard Override
# ---------------------------------------------------------------------------


class TestComplianceOverride:
    def test_compliance_override_going_concern(self, all_reports, compliance_going_concern):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        overridden = model.apply_compliance_override(verdict, compliance_going_concern)
        assert overridden.final_signal == "SELL"
        assert any("going_concern" in d for d in overridden.key_drivers)

    def test_compliance_override_restatement(self, all_reports, compliance_restatement):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        overridden = model.apply_compliance_override(verdict, compliance_restatement)
        assert overridden.final_signal == "SELL"
        assert any("restatement" in d for d in overridden.key_drivers)

    def test_compliance_override_no_flags(self, all_reports, compliance_report):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        original_signal = verdict.final_signal
        overridden = model.apply_compliance_override(verdict, compliance_report)
        assert overridden.final_signal == original_signal

    def test_compliance_override_none_report(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        verdict = model.predict(all_reports)
        original_signal = verdict.final_signal
        overridden = model.apply_compliance_override(verdict, None)
        assert overridden.final_signal == original_signal


# ---------------------------------------------------------------------------
# Strong Signal Thresholds
# ---------------------------------------------------------------------------


class TestStrongSignalThresholds:
    def test_strong_buy_requires_high_confidence(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        # Value > 0.3 but low confidence should be BUY not STRONG_BUY
        signal = model.numeric_to_signal(0.8, 0.60)
        assert signal == "BUY"

    def test_strong_sell_requires_high_confidence(self):
        from models.signal_fusion import SignalFusionModel

        model = SignalFusionModel()
        signal = model.numeric_to_signal(-0.8, 0.60)
        assert signal == "SELL"


# ---------------------------------------------------------------------------
# Custom Weights
# ---------------------------------------------------------------------------


class TestCustomWeights:
    def test_custom_weights(self, all_reports):
        from models.signal_fusion import SignalFusionModel

        custom_weights = {
            "ValuationScout": 0.40,
            "MomentumTracker": 0.15,
            "PulseMonitor": 0.15,
            "EconomyWatcher": 0.15,
            "ComplianceChecker": 0.15,
        }
        model = SignalFusionModel(weights=custom_weights)
        assert model.weights["ValuationScout"] == 0.40
        signal, conf = model.weighted_average_predict(all_reports)
        assert signal in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL")
        assert 0.0 < conf <= 1.0
