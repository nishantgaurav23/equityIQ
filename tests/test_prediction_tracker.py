"""Tests for PredictionTracker (S16.3)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from config.data_contracts import FinalVerdict
from evaluation.prediction_tracker import (
    PredictionTracker,
    WeightAdjustment,
)


def _utcnow():
    return datetime.now(timezone.utc)


def _make_verdict(
    ticker: str = "AAPL",
    signal: str = "BUY",
    confidence: float = 0.80,
    analyst_signals: dict | None = None,
    session_id: str | None = None,
    timestamp: datetime | None = None,
) -> FinalVerdict:
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        analyst_signals=analyst_signals or {
            "ValuationScout": "BUY",
            "MomentumTracker": "BUY",
            "PulseMonitor": "HOLD",
            "EconomyWatcher": "HOLD",
            "ComplianceChecker": "BUY",
        },
        key_drivers=["test"],
        session_id=session_id or str(uuid.uuid4()),
        timestamp=timestamp or _utcnow(),
    )


@pytest_asyncio.fixture
async def tracker(tmp_path):
    """Create a PredictionTracker with in-memory-like temp DB."""
    db_path = str(tmp_path / "predictions.db")
    mock_history = AsyncMock()
    mock_history.get_ticker_history = AsyncMock(return_value=[])

    async def mock_price_lookup(ticker: str, date: datetime) -> float | None:
        return 150.0

    pt = PredictionTracker(
        history_retriever=mock_history,
        price_lookup=mock_price_lookup,
        db_path=db_path,
    )
    await pt.initialize()
    yield pt
    await pt.close()


# ---------------------------------------------------------------------------
# FR-2: Track predictions
# ---------------------------------------------------------------------------


class TestTrackPrediction:
    @pytest.mark.asyncio
    async def test_creates_outcomes_for_all_windows(self, tracker):
        verdict = _make_verdict()
        outcomes = await tracker.track_prediction(verdict, price_at_prediction=150.0)
        assert len(outcomes) == 3  # 30, 60, 90 day windows
        windows = {o.check_window_days for o in outcomes}
        assert windows == {30, 60, 90}

    @pytest.mark.asyncio
    async def test_outcomes_are_pending(self, tracker):
        verdict = _make_verdict()
        outcomes = await tracker.track_prediction(verdict, price_at_prediction=150.0)
        for o in outcomes:
            assert o.outcome == "pending"
            assert o.ticker == "AAPL"
            assert o.predicted_signal == "BUY"
            assert o.predicted_confidence == 0.80
            assert o.price_at_prediction == 150.0

    @pytest.mark.asyncio
    async def test_outcomes_stored_in_db(self, tracker):
        verdict = _make_verdict()
        await tracker.track_prediction(verdict, price_at_prediction=150.0)
        scorecard = await tracker.get_accuracy_scorecard()
        assert scorecard.total_predictions == 3
        assert scorecard.pending_predictions == 3


# ---------------------------------------------------------------------------
# FR-3: Check pending predictions
# ---------------------------------------------------------------------------


class TestCheckPending:
    @pytest.mark.asyncio
    async def test_resolves_mature_predictions(self, tracker):
        # Create a verdict from 35 days ago
        old_time = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(timestamp=old_time)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        # Price went up -- BUY should be correct
        async def price_up(ticker, date):
            return 120.0  # 20% gain

        tracker._price_lookup = price_up
        resolved = await tracker.check_pending_predictions()

        # Only 30-day window should be mature (35 > 30)
        assert len(resolved) >= 1
        for r in resolved:
            if r.check_window_days == 30:
                assert r.outcome == "correct"
                assert r.actual_return_pct == pytest.approx(0.20, abs=0.01)

    @pytest.mark.asyncio
    async def test_skips_immature_predictions(self, tracker):
        # Create a verdict from 5 days ago (too recent)
        recent = _utcnow() - timedelta(days=5)
        verdict = _make_verdict(timestamp=recent)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        resolved = await tracker.check_pending_predictions()
        assert len(resolved) == 0

    @pytest.mark.asyncio
    async def test_sell_signal_correct_on_price_drop(self, tracker):
        old_time = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(signal="SELL", timestamp=old_time)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        async def price_down(ticker, date):
            return 80.0  # 20% loss

        tracker._price_lookup = price_down
        resolved = await tracker.check_pending_predictions()
        mature = [r for r in resolved if r.check_window_days == 30]
        assert len(mature) == 1
        assert mature[0].outcome == "correct"

    @pytest.mark.asyncio
    async def test_buy_incorrect_on_price_drop(self, tracker):
        old_time = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(signal="BUY", timestamp=old_time)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        async def price_down(ticker, date):
            return 80.0

        tracker._price_lookup = price_down
        resolved = await tracker.check_pending_predictions()
        mature = [r for r in resolved if r.check_window_days == 30]
        assert len(mature) == 1
        assert mature[0].outcome == "incorrect"


# ---------------------------------------------------------------------------
# FR-4: Accuracy scorecard
# ---------------------------------------------------------------------------


class TestAccuracyScorecard:
    @pytest.mark.asyncio
    async def test_computation(self, tracker):
        # Create two old verdicts: one correct, one incorrect
        t1 = _utcnow() - timedelta(days=35)
        v1 = _make_verdict(signal="BUY", timestamp=t1, session_id="s1")
        await tracker.track_prediction(v1, price_at_prediction=100.0)

        t2 = _utcnow() - timedelta(days=35)
        v2 = _make_verdict(signal="BUY", timestamp=t2, session_id="s2")
        await tracker.track_prediction(v2, price_at_prediction=100.0)

        # Resolve: v1 correct, v2 incorrect
        call_count = 0

        async def mixed_prices(ticker, date):
            nonlocal call_count
            call_count += 1
            # All check lookups alternate
            return 120.0 if call_count % 2 == 1 else 80.0

        tracker._price_lookup = mixed_prices
        await tracker.check_pending_predictions()

        scorecard = await tracker.get_accuracy_scorecard()
        assert scorecard.total_predictions == 6  # 2 verdicts * 3 windows
        assert scorecard.resolved_predictions >= 2  # at least 30-day windows

    @pytest.mark.asyncio
    async def test_per_ticker(self, tracker):
        t = _utcnow() - timedelta(days=35)
        v1 = _make_verdict(ticker="AAPL", timestamp=t, session_id="s1")
        v2 = _make_verdict(ticker="MSFT", timestamp=t, session_id="s2")
        await tracker.track_prediction(v1, price_at_prediction=100.0)
        await tracker.track_prediction(v2, price_at_prediction=200.0)

        scorecard_aapl = await tracker.get_accuracy_scorecard(ticker="AAPL")
        assert scorecard_aapl.total_predictions == 3

        scorecard_msft = await tracker.get_accuracy_scorecard(ticker="MSFT")
        assert scorecard_msft.total_predictions == 3

    @pytest.mark.asyncio
    async def test_empty_returns_zero_scorecard(self, tracker):
        scorecard = await tracker.get_accuracy_scorecard()
        assert scorecard.total_predictions == 0
        assert scorecard.hit_rate == 0.0
        assert scorecard.resolved_predictions == 0


# ---------------------------------------------------------------------------
# FR-5: Per-agent accuracy
# ---------------------------------------------------------------------------


class TestAgentAccuracy:
    @pytest.mark.asyncio
    async def test_attribution(self, tracker):
        t = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(
            signal="BUY",
            timestamp=t,
            analyst_signals={
                "ValuationScout": "BUY",
                "MomentumTracker": "SELL",
                "PulseMonitor": "BUY",
                "EconomyWatcher": "HOLD",
                "ComplianceChecker": "BUY",
            },
        )
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        # Price goes up -- BUY was correct
        async def price_up(ticker, date):
            return 120.0

        tracker._price_lookup = price_up
        await tracker.check_pending_predictions()

        agent_acc = await tracker.get_agent_accuracy()
        # ValuationScout said BUY, price went up -> correct
        assert "ValuationScout" in agent_acc
        assert agent_acc["ValuationScout"].accuracy > 0


# ---------------------------------------------------------------------------
# FR-6: Weight adjustment
# ---------------------------------------------------------------------------


class TestWeightAdjustment:
    @pytest.mark.asyncio
    async def test_formula(self, tracker):
        # Seed enough data (20+ predictions resolved)
        for i in range(8):
            t = _utcnow() - timedelta(days=35 + i)
            v = _make_verdict(signal="BUY", timestamp=t, session_id=f"s{i}")
            await tracker.track_prediction(v, price_at_prediction=100.0)

        async def price_up(ticker, date):
            return 120.0

        tracker._price_lookup = price_up
        await tracker.check_pending_predictions()

        adj = await tracker.recommend_weight_adjustments()
        assert isinstance(adj, WeightAdjustment)
        assert len(adj.current_weights) > 0
        # Weights should sum to ~1.0
        if adj.recommended_weights:
            total = sum(adj.recommended_weights.values())
            assert total == pytest.approx(1.0, abs=0.01)

    @pytest.mark.asyncio
    async def test_insufficient_data(self, tracker):
        adj = await tracker.recommend_weight_adjustments()
        assert adj.confidence == "low"


# ---------------------------------------------------------------------------
# FR-7: Dashboard summary
# ---------------------------------------------------------------------------


class TestScorecardSummary:
    @pytest.mark.asyncio
    async def test_combined(self, tracker):
        summary = await tracker.get_scorecard_summary()
        assert "scorecard" in summary
        assert "agent_accuracy" in summary
        assert "weight_adjustment" in summary
        assert "recent_outcomes" in summary


# ---------------------------------------------------------------------------
# FR-8: Graceful degradation
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_price_lookup_failure(self, tracker):
        t = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(timestamp=t)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        async def failing_lookup(ticker, date):
            raise ConnectionError("API down")

        tracker._price_lookup = failing_lookup
        # Should not crash
        resolved = await tracker.check_pending_predictions()
        assert len(resolved) == 0  # All stay pending

    @pytest.mark.asyncio
    async def test_price_returns_none(self, tracker):
        t = _utcnow() - timedelta(days=35)
        verdict = _make_verdict(timestamp=t)
        await tracker.track_prediction(verdict, price_at_prediction=100.0)

        async def none_lookup(ticker, date):
            return None

        tracker._price_lookup = none_lookup
        resolved = await tracker.check_pending_predictions()
        assert len(resolved) == 0  # All stay pending
