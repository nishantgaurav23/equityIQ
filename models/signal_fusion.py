"""XGBoost signal synthesis -- fuses 5 analyst signals into a final verdict."""

import logging
import uuid

import numpy as np
from xgboost import XGBClassifier

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    FinalVerdict,
    MomentumReport,
    PulseReport,
    ValuationReport,
)

logger = logging.getLogger(__name__)

# Default signal weights per agent
DEFAULT_WEIGHTS: dict[str, float] = {
    "ValuationScout": 0.25,
    "MomentumTracker": 0.20,
    "PulseMonitor": 0.20,
    "EconomyWatcher": 0.20,
    "ComplianceChecker": 0.15,
}

# Macro regime to numeric mapping
REGIME_MAP: dict[str, float] = {
    "expansion": 1.0,
    "recovery": 0.5,
    "contraction": -0.5,
    "stagflation": -1.0,
}

# Signal to numeric mapping
SIGNAL_MAP: dict[str, float] = {
    "BUY": 1.0,
    "HOLD": 0.0,
    "SELL": -1.0,
}

# Agent name to report type mapping
AGENT_TYPE_MAP: dict[str, type] = {
    "ValuationScout": ValuationReport,
    "MomentumTracker": MomentumReport,
    "PulseMonitor": PulseReport,
    "EconomyWatcher": EconomyReport,
    "ComplianceChecker": ComplianceReport,
}

# Agent name to short key mapping
AGENT_KEY_MAP: dict[str, str] = {
    "ValuationScout": "valuation",
    "MomentumTracker": "momentum",
    "PulseMonitor": "pulse",
    "EconomyWatcher": "economy",
    "ComplianceChecker": "compliance",
}

# Label encoding for XGBoost
LABEL_MAP: dict[str, int] = {"BUY": 0, "HOLD": 1, "SELL": 2}
LABEL_REVERSE: dict[int, str] = {0: "BUY", 1: "HOLD", 2: "SELL"}

# Confidence reduction per missing agent
MISSING_AGENT_PENALTY = 0.20


def _safe_float(value, default: float = 0.0) -> float:
    """Convert value to float, returning default for None."""
    if value is None:
        return default
    return float(value)


class SignalFusionModel:
    """Fuses analyst signals into a final verdict via XGBoost or weighted average."""

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or dict(DEFAULT_WEIGHTS)
        self.model: XGBClassifier | None = None
        self.is_trained: bool = False
        self._feature_names: list[str] = []

    # -------------------------------------------------------------------
    # FR-2: Signal encoding / decoding
    # -------------------------------------------------------------------

    @staticmethod
    def signal_to_numeric(signal: str) -> float:
        """BUY -> 1.0, HOLD -> 0.0, SELL -> -1.0."""
        return SIGNAL_MAP.get(signal, 0.0)

    @staticmethod
    def numeric_to_signal(value: float, confidence: float) -> str:
        """Map numeric prediction + confidence to 5-level signal."""
        if value > 0.3:
            return "STRONG_BUY" if confidence >= 0.75 else "BUY"
        if value < -0.3:
            return "STRONG_SELL" if confidence >= 0.75 else "SELL"
        return "HOLD"

    # -------------------------------------------------------------------
    # FR-1: Feature extraction
    # -------------------------------------------------------------------

    def extract_features(self, reports: list) -> dict[str, float]:
        """Convert analyst reports into a flat feature dictionary."""
        # Index reports by agent name
        by_agent: dict[str, object] = {}
        for r in reports:
            by_agent[r.agent_name] = r

        features: dict[str, float] = {}

        # Valuation features
        key = "valuation"
        if "ValuationScout" in by_agent:
            r = by_agent["ValuationScout"]
            features[f"{key}_missing"] = 0.0
            features[f"{key}_signal"] = self.signal_to_numeric(r.signal)
            features[f"{key}_confidence"] = r.confidence
            features[f"{key}_pe_ratio"] = _safe_float(r.pe_ratio)
            features[f"{key}_pb_ratio"] = _safe_float(r.pb_ratio)
            features[f"{key}_revenue_growth"] = _safe_float(r.revenue_growth)
            features[f"{key}_debt_to_equity"] = _safe_float(r.debt_to_equity)
            features[f"{key}_fcf_yield"] = _safe_float(r.fcf_yield)
            features[f"{key}_intrinsic_value_gap"] = _safe_float(r.intrinsic_value_gap)
        else:
            features[f"{key}_missing"] = 1.0
            for f in [
                "signal",
                "confidence",
                "pe_ratio",
                "pb_ratio",
                "revenue_growth",
                "debt_to_equity",
                "fcf_yield",
                "intrinsic_value_gap",
            ]:
                features[f"{key}_{f}"] = 0.0

        # Momentum features
        key = "momentum"
        if "MomentumTracker" in by_agent:
            r = by_agent["MomentumTracker"]
            features[f"{key}_missing"] = 0.0
            features[f"{key}_signal"] = self.signal_to_numeric(r.signal)
            features[f"{key}_confidence"] = r.confidence
            features[f"{key}_rsi_14"] = _safe_float(r.rsi_14)
            features[f"{key}_macd_signal"] = _safe_float(r.macd_signal)
            features[f"{key}_price_momentum_score"] = _safe_float(r.price_momentum_score)
            features[f"{key}_above_sma_50"] = 1.0 if r.above_sma_50 else 0.0
            features[f"{key}_above_sma_200"] = 1.0 if r.above_sma_200 else 0.0
        else:
            features[f"{key}_missing"] = 1.0
            for f in [
                "signal",
                "confidence",
                "rsi_14",
                "macd_signal",
                "price_momentum_score",
                "above_sma_50",
                "above_sma_200",
            ]:
                features[f"{key}_{f}"] = 0.0

        # Pulse features
        key = "pulse"
        if "PulseMonitor" in by_agent:
            r = by_agent["PulseMonitor"]
            features[f"{key}_missing"] = 0.0
            features[f"{key}_signal"] = self.signal_to_numeric(r.signal)
            features[f"{key}_confidence"] = r.confidence
            features[f"{key}_sentiment_score"] = _safe_float(r.sentiment_score)
            features[f"{key}_article_count"] = float(r.article_count)
        else:
            features[f"{key}_missing"] = 1.0
            for f in ["signal", "confidence", "sentiment_score", "article_count"]:
                features[f"{key}_{f}"] = 0.0

        # Economy features
        key = "economy"
        if "EconomyWatcher" in by_agent:
            r = by_agent["EconomyWatcher"]
            features[f"{key}_missing"] = 0.0
            features[f"{key}_signal"] = self.signal_to_numeric(r.signal)
            features[f"{key}_confidence"] = r.confidence
            features[f"{key}_gdp_growth"] = _safe_float(r.gdp_growth)
            features[f"{key}_inflation_rate"] = _safe_float(r.inflation_rate)
            features[f"{key}_fed_funds_rate"] = _safe_float(r.fed_funds_rate)
            features[f"{key}_unemployment_rate"] = _safe_float(r.unemployment_rate)
            features[f"{key}_macro_regime_numeric"] = REGIME_MAP.get(r.macro_regime or "", 0.0)
        else:
            features[f"{key}_missing"] = 1.0
            for f in [
                "signal",
                "confidence",
                "gdp_growth",
                "inflation_rate",
                "fed_funds_rate",
                "unemployment_rate",
                "macro_regime_numeric",
            ]:
                features[f"{key}_{f}"] = 0.0

        # Compliance features
        key = "compliance"
        if "ComplianceChecker" in by_agent:
            r = by_agent["ComplianceChecker"]
            features[f"{key}_missing"] = 0.0
            features[f"{key}_signal"] = self.signal_to_numeric(r.signal)
            features[f"{key}_confidence"] = r.confidence
            features[f"{key}_risk_score"] = _safe_float(r.risk_score)
            features[f"{key}_days_since_filing"] = _safe_float(r.days_since_filing)
            flags = r.risk_flags or []
            features[f"{key}_has_going_concern"] = 1.0 if "going_concern" in flags else 0.0
            features[f"{key}_has_restatement"] = 1.0 if "restatement" in flags else 0.0
        else:
            features[f"{key}_missing"] = 1.0
            for f in [
                "signal",
                "confidence",
                "risk_score",
                "days_since_filing",
                "has_going_concern",
                "has_restatement",
            ]:
                features[f"{key}_{f}"] = 0.0

        return features

    # -------------------------------------------------------------------
    # FR-3: Weighted average fallback
    # -------------------------------------------------------------------

    def weighted_average_predict(self, reports: list) -> tuple[str, float]:
        """Fallback prediction using weighted average of signals."""
        if not reports:
            return ("HOLD", 0.0)

        by_agent: dict[str, object] = {}
        for r in reports:
            by_agent[r.agent_name] = r

        weighted_signal = 0.0
        weighted_conf = 0.0
        total_weight = 0.0
        missing_count = 0

        for agent_name, weight in self.weights.items():
            if agent_name in by_agent:
                r = by_agent[agent_name]
                sig_num = self.signal_to_numeric(r.signal)
                weighted_signal += sig_num * r.confidence * weight
                weighted_conf += r.confidence * weight
                total_weight += weight
            else:
                missing_count += 1

        if total_weight == 0.0:
            return ("HOLD", 0.0)

        avg_signal = weighted_signal / total_weight
        avg_conf = weighted_conf / total_weight

        # Reduce confidence for missing agents
        avg_conf = max(0.0, avg_conf - missing_count * MISSING_AGENT_PENALTY)
        avg_conf = min(1.0, avg_conf)

        signal = self.numeric_to_signal(avg_signal, avg_conf)
        return (signal, avg_conf)

    # -------------------------------------------------------------------
    # FR-4: XGBoost training
    # -------------------------------------------------------------------

    def fit(self, training_data: list[tuple[list, str]]) -> None:
        """Train XGBoost classifier on historical analyst reports."""
        if not training_data:
            raise ValueError("Training data cannot be empty")

        if len(training_data) < 10:
            logger.warning("Training with fewer than 10 samples (%d)", len(training_data))

        X_rows = []
        y_labels = []

        for reports, outcome in training_data:
            features = self.extract_features(reports)
            # Ensure consistent feature ordering
            if not self._feature_names:
                self._feature_names = sorted(features.keys())
            row = [features.get(f, 0.0) for f in self._feature_names]
            X_rows.append(row)
            y_labels.append(LABEL_MAP[outcome])

        X = np.array(X_rows, dtype=np.float32)
        y = np.array(y_labels, dtype=np.int32)

        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
        )
        self.model.fit(X, y)
        self.is_trained = True
        logger.info("SignalFusionModel trained on %d samples", len(training_data))

    # -------------------------------------------------------------------
    # FR-5: Prediction
    # -------------------------------------------------------------------

    def predict(self, reports: list) -> FinalVerdict:
        """Predict final verdict from analyst reports."""
        if not reports:
            return FinalVerdict(
                ticker="",
                final_signal="HOLD",
                overall_confidence=0.0,
                session_id=str(uuid.uuid4()),
            )

        ticker = reports[0].ticker

        # Build analyst_signals dict and key_drivers
        analyst_signals: dict[str, str] = {}
        key_drivers: list[str] = []
        for r in reports:
            analyst_signals[r.agent_name] = r.signal
            key_drivers.append(f"{r.agent_name}: {r.signal} ({r.confidence:.0%})")

        if self.is_trained and self.model is not None:
            signal, confidence = self._xgboost_predict(reports)
        else:
            signal, confidence = self.weighted_average_predict(reports)

        # Find compliance report for override
        compliance_report = None
        for r in reports:
            if isinstance(r, ComplianceReport):
                compliance_report = r
                break

        verdict = FinalVerdict(
            ticker=ticker,
            final_signal=signal,
            overall_confidence=confidence,
            analyst_signals=analyst_signals,
            key_drivers=key_drivers,
            session_id=str(uuid.uuid4()),
        )

        # Apply compliance override
        verdict = self.apply_compliance_override(verdict, compliance_report)

        return verdict

    def _xgboost_predict(self, reports: list) -> tuple[str, float]:
        """Use trained XGBoost model for prediction."""
        features = self.extract_features(reports)
        row = [features.get(f, 0.0) for f in self._feature_names]
        X = np.array([row], dtype=np.float32)

        proba = self.model.predict_proba(X)[0]
        pred_label = int(np.argmax(proba))
        confidence = float(proba[pred_label])

        base_signal = LABEL_REVERSE[pred_label]
        signal_numeric = self.signal_to_numeric(base_signal)
        signal = self.numeric_to_signal(signal_numeric, confidence)

        return (signal, confidence)

    # -------------------------------------------------------------------
    # FR-6: Compliance hard override
    # -------------------------------------------------------------------

    @staticmethod
    def apply_compliance_override(
        verdict: FinalVerdict, compliance_report: ComplianceReport | None
    ) -> FinalVerdict:
        """Force SELL if going_concern or restatement detected."""
        if compliance_report is None:
            return verdict

        flags = compliance_report.risk_flags or []
        override_reasons: list[str] = []

        if "going_concern" in flags:
            override_reasons.append("Compliance override: going_concern detected")
        if "restatement" in flags:
            override_reasons.append("Compliance override: restatement detected")

        if override_reasons:
            verdict.final_signal = "SELL"
            verdict.key_drivers = verdict.key_drivers + override_reasons

        return verdict
