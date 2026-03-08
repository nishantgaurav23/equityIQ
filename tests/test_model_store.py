"""Tests for models/model_store.py -- model persistence with joblib."""

import time

import pytest

from config.data_contracts import (
    ComplianceReport,
    EconomyReport,
    MomentumReport,
    PulseReport,
    ValuationReport,
)
from models.model_store import ModelStore
from models.signal_fusion import SignalFusionModel

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
        signal="HOLD",
        confidence=0.70,
        reasoning="Clean filings",
        latest_filing_type="10-K",
        days_since_filing=30,
        risk_flags=[],
        risk_score=0.15,
    )


@pytest.fixture
def all_reports(
    valuation_report, momentum_report, pulse_report, economy_report, compliance_report
):
    return [valuation_report, momentum_report, pulse_report, economy_report, compliance_report]


@pytest.fixture
def trained_model(all_reports):
    """Create a trained SignalFusionModel for testing."""
    model = SignalFusionModel()
    training_data = (
        [(all_reports, "BUY")] * 5
        + [(all_reports, "HOLD")] * 5
        + [(all_reports, "SELL")] * 5
    )
    model.fit(training_data)
    return model


@pytest.fixture
def store(tmp_path):
    """ModelStore backed by a temp directory."""
    return ModelStore(base_dir=tmp_path)


# ---------------------------------------------------------------------------
# Test: Import
# ---------------------------------------------------------------------------


class TestImport:
    def test_model_store_import(self):
        from models.model_store import ModelInfo, ModelStore  # noqa: F811

        assert ModelStore is not None
        assert ModelInfo is not None


# ---------------------------------------------------------------------------
# Test: Save
# ---------------------------------------------------------------------------


class TestSave:
    def test_save_trained_model(self, store, trained_model):
        path = store.save(trained_model)
        assert path.exists()
        assert path.suffix == ".joblib"
        assert "signal_fusion_" in path.name

    def test_save_untrained_model_raises(self, store):
        model = SignalFusionModel()
        with pytest.raises(ValueError, match="untrained"):
            store.save(model)

    def test_save_with_tag(self, store, trained_model):
        path = store.save(trained_model, tag="production")
        assert "production" in path.name

    def test_save_invalid_tag_raises(self, store, trained_model):
        with pytest.raises(ValueError, match="tag"):
            store.save(trained_model, tag="../escape")

    def test_save_invalid_tag_slash_raises(self, store, trained_model):
        with pytest.raises(ValueError, match="tag"):
            store.save(trained_model, tag="bad/tag")

    def test_creates_directory(self, tmp_path, trained_model):
        subdir = tmp_path / "nested" / "models"
        s = ModelStore(base_dir=subdir)
        path = s.save(trained_model)
        assert path.exists()
        assert subdir.exists()


# ---------------------------------------------------------------------------
# Test: Load
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_specific_path(self, store, trained_model, all_reports):
        path = store.save(trained_model)
        loaded = store.load(path)
        assert isinstance(loaded, SignalFusionModel)
        assert loaded.is_trained is True
        # Can still predict
        verdict = loaded.predict(all_reports)
        assert verdict.ticker == "AAPL"

    def test_load_latest(self, store, trained_model):
        store.save(trained_model, tag="old")
        time.sleep(0.05)  # ensure different timestamps
        store.save(trained_model, tag="new")
        loaded = store.load()
        assert loaded.is_trained is True

    def test_load_nonexistent_raises(self, store, tmp_path):
        with pytest.raises(FileNotFoundError):
            store.load(tmp_path / "nonexistent.joblib")

    def test_load_empty_dir_raises(self, store):
        with pytest.raises(FileNotFoundError, match="No saved models"):
            store.load()

    def test_load_wrong_type_raises(self, store, tmp_path):
        import joblib

        bad_path = tmp_path / "not_a_model.joblib"
        joblib.dump({"not": "a model"}, bad_path)
        with pytest.raises(TypeError, match="SignalFusionModel"):
            store.load(bad_path)

    def test_round_trip_predict(self, store, trained_model, all_reports):
        """Save -> load -> predict gives same results."""
        original_verdict = trained_model.predict(all_reports)
        path = store.save(trained_model)
        loaded = store.load(path)
        loaded_verdict = loaded.predict(all_reports)
        assert original_verdict.final_signal == loaded_verdict.final_signal
        assert abs(original_verdict.overall_confidence - loaded_verdict.overall_confidence) < 0.01


# ---------------------------------------------------------------------------
# Test: List
# ---------------------------------------------------------------------------


class TestList:
    def test_list_models_empty(self, store):
        result = store.list()
        assert result == []

    def test_list_models_sorted(self, store, trained_model):
        store.save(trained_model, tag="first")
        time.sleep(0.05)
        store.save(trained_model, tag="second")
        result = store.list()
        assert len(result) == 2
        # Newest first
        assert "second" in result[0].filename
        assert "first" in result[1].filename

    def test_list_models_metadata(self, store, trained_model):
        store.save(trained_model, tag="v1")
        result = store.list()
        assert len(result) == 1
        info = result[0]
        assert info.path.exists()
        assert "v1" in info.filename
        assert info.tag == "v1"
        assert info.timestamp is not None
        assert info.size_bytes > 0


# ---------------------------------------------------------------------------
# Test: Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_model(self, store, trained_model):
        path = store.save(trained_model)
        assert path.exists()
        result = store.delete(path)
        assert result is True
        assert not path.exists()

    def test_delete_nonexistent(self, store, tmp_path):
        result = store.delete(tmp_path / "nonexistent.joblib")
        assert result is False

    def test_delete_outside_base_dir_raises(self, tmp_path):
        import joblib

        # Create store in a subdirectory
        store = ModelStore(base_dir=tmp_path / "models")
        (tmp_path / "models").mkdir()

        outside = tmp_path / "elsewhere" / "model.joblib"
        outside.parent.mkdir(parents=True)
        joblib.dump("fake", outside)
        with pytest.raises(ValueError, match="data/models"):
            store.delete(outside)


# ---------------------------------------------------------------------------
# Test: Get Latest Path
# ---------------------------------------------------------------------------


class TestGetLatestPath:
    def test_get_latest_path(self, store, trained_model):
        store.save(trained_model, tag="old")
        time.sleep(0.05)
        path2 = store.save(trained_model, tag="new")
        latest = store.get_latest_path()
        assert latest == path2

    def test_get_latest_path_empty(self, store):
        result = store.get_latest_path()
        assert result is None
