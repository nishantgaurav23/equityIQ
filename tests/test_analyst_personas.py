"""Tests for config/analyst_personas.py -- S2.3 Agent Personas."""

from config.analyst_personas import PERSONAS

REQUIRED_KEYS = [
    "valuation_scout",
    "momentum_tracker",
    "pulse_monitor",
    "economy_watcher",
    "compliance_checker",
    "signal_synthesizer",
    "risk_guardian",
]


class TestPersonasStructure:
    def test_personas_importable(self):
        assert PERSONAS is not None

    def test_personas_is_dict(self):
        assert isinstance(PERSONAS, dict)

    def test_personas_has_seven_keys(self):
        assert len(PERSONAS) == 7

    def test_personas_required_keys(self):
        for key in REQUIRED_KEYS:
            assert key in PERSONAS, f"Missing key: {key}"

    def test_personas_values_are_strings(self):
        for key, value in PERSONAS.items():
            assert isinstance(value, str), f"PERSONAS['{key}'] is not a string"

    def test_personas_values_non_empty(self):
        for key, value in PERSONAS.items():
            assert len(value) > 50, f"PERSONAS['{key}'] is too short ({len(value)} chars)"


class TestValuationScoutContent:
    def test_mentions_valuation_ratios(self):
        prompt = PERSONAS["valuation_scout"].lower()
        assert "p/e" in prompt or "pe_ratio" in prompt or "price-to-earnings" in prompt

    def test_mentions_intrinsic_value(self):
        prompt = PERSONAS["valuation_scout"].lower()
        assert "intrinsic" in prompt or "valuation" in prompt

    def test_mentions_output_schema(self):
        prompt = PERSONAS["valuation_scout"]
        assert "ValuationReport" in prompt


class TestMomentumTrackerContent:
    def test_mentions_technical_indicators(self):
        prompt = PERSONAS["momentum_tracker"].lower()
        assert "rsi" in prompt
        assert "macd" in prompt

    def test_mentions_sma(self):
        prompt = PERSONAS["momentum_tracker"].lower()
        assert "sma" in prompt or "moving average" in prompt

    def test_mentions_output_schema(self):
        prompt = PERSONAS["momentum_tracker"]
        assert "MomentumReport" in prompt


class TestPulseMonitorContent:
    def test_mentions_sentiment(self):
        prompt = PERSONAS["pulse_monitor"].lower()
        assert "sentiment" in prompt

    def test_confidence_cap_rule(self):
        prompt = PERSONAS["pulse_monitor"]
        has_threshold = "0.70" in prompt or "0.7" in prompt
        has_article_ref = (
            "3 article" in prompt or "fewer than 3" in prompt or "article_count" in prompt
        )
        assert has_threshold and has_article_ref, (
            "PulseMonitor must mention confidence cap of 0.70 with < 3 articles"
        )

    def test_mentions_output_schema(self):
        prompt = PERSONAS["pulse_monitor"]
        assert "PulseReport" in prompt


class TestEconomyWatcherContent:
    def test_mentions_macro_indicators(self):
        prompt = PERSONAS["economy_watcher"].lower()
        assert "gdp" in prompt
        assert "inflation" in prompt

    def test_mentions_macro_regime(self):
        prompt = PERSONAS["economy_watcher"].lower()
        assert "regime" in prompt or "expansion" in prompt or "contraction" in prompt

    def test_mentions_output_schema(self):
        prompt = PERSONAS["economy_watcher"]
        assert "EconomyReport" in prompt


class TestComplianceCheckerContent:
    def test_sell_override_rule(self):
        prompt = PERSONAS["compliance_checker"]
        assert "going_concern" in prompt
        assert "restatement" in prompt
        assert "SELL" in prompt

    def test_mentions_sec_filings(self):
        prompt = PERSONAS["compliance_checker"].lower()
        assert "sec" in prompt or "filing" in prompt

    def test_mentions_output_schema(self):
        prompt = PERSONAS["compliance_checker"]
        assert "ComplianceReport" in prompt


class TestSignalSynthesizerContent:
    def test_strong_signal_threshold(self):
        prompt = PERSONAS["signal_synthesizer"]
        assert "0.75" in prompt
        assert "STRONG" in prompt or "strong" in prompt.lower()

    def test_mentions_weights(self):
        prompt = PERSONAS["signal_synthesizer"]
        assert "0.25" in prompt or "weight" in prompt.lower()

    def test_mentions_output_schema(self):
        prompt = PERSONAS["signal_synthesizer"]
        assert "FinalVerdict" in prompt


class TestRiskGuardianContent:
    def test_position_size_limit(self):
        prompt = PERSONAS["risk_guardian"]
        has_limit = "0.10" in prompt or "10%" in prompt
        has_position = "position" in prompt.lower()
        assert has_limit and has_position, (
            "RiskGuardian must mention 0.10 / 10% position size limit"
        )

    def test_mentions_risk_metrics(self):
        prompt = PERSONAS["risk_guardian"].lower()
        assert "volatility" in prompt or "beta" in prompt

    def test_mentions_output_schema(self):
        prompt = PERSONAS["risk_guardian"]
        assert "RiskGuardianReport" in prompt
