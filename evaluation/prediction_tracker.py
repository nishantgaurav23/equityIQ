"""Prediction accuracy tracker (S16.3).

Tracks past FinalVerdicts against actual price movement across 30/60/90 day
windows. Computes per-agent and overall accuracy. Recommends signal weight
adjustments based on historical performance.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

import aiosqlite
from pydantic import BaseModel, field_validator

from config.data_contracts import FinalVerdict, PredictionOutcome
from evaluation.backtester import is_signal_correct
from models.signal_fusion import DEFAULT_WEIGHTS

logger = logging.getLogger(__name__)

# Type alias for async price lookup
PriceLookup = Callable[[str, datetime], float | None]

DEFAULT_WINDOWS = [30, 60, 90]


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class AccuracyScorecard(BaseModel):
    """Aggregated prediction accuracy metrics."""

    total_predictions: int = 0
    resolved_predictions: int = 0
    pending_predictions: int = 0
    accuracy_by_window: dict[int, float] = {}
    accuracy_by_signal: dict[str, float] = {}
    hit_rate: float = 0.0
    confidence_calibration: float = 0.0

    @field_validator("hit_rate", "confidence_calibration", mode="before")
    @classmethod
    def clamp_rate(cls, v):
        if v is None:
            return 0.0
        return max(0.0, min(1.0, float(v)))


class AgentAccuracy(BaseModel):
    """Per-agent prediction accuracy."""

    agent_name: str
    total_signals: int = 0
    correct_signals: int = 0
    accuracy: float = 0.0
    avg_confidence: float = 0.0


class WeightAdjustment(BaseModel):
    """Recommended signal weight changes based on accuracy."""

    current_weights: dict[str, float] = {}
    recommended_weights: dict[str, float] = {}
    agent_accuracies: dict[str, float] = {}
    min_predictions_required: int = 20
    confidence: str = "low"


# ---------------------------------------------------------------------------
# PredictionTracker
# ---------------------------------------------------------------------------


class PredictionTracker:
    """Tracks and evaluates prediction accuracy over time."""

    def __init__(
        self,
        history_retriever,
        price_lookup: PriceLookup,
        db_path: str = "predictions.db",
        windows: list[int] | None = None,
    ):
        self._history = history_retriever
        self._price_lookup = price_lookup
        self._db_path = db_path
        self._windows = windows or list(DEFAULT_WINDOWS)
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open DB and create table if needed."""
        self._conn = await aiosqlite.connect(self._db_path)
        await self._conn.execute(
            """CREATE TABLE IF NOT EXISTS prediction_outcomes (
                outcome_id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                verdict_session_id TEXT NOT NULL,
                predicted_signal TEXT NOT NULL,
                predicted_confidence REAL NOT NULL,
                price_at_prediction REAL NOT NULL,
                price_at_check REAL,
                actual_return_pct REAL,
                check_window_days INTEGER NOT NULL,
                outcome TEXT NOT NULL DEFAULT 'pending',
                analyst_signals_json TEXT,
                created_at TEXT NOT NULL,
                checked_at TEXT
            )"""
        )
        await self._conn.commit()

    async def close(self) -> None:
        """Close DB connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _ensure_conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            await self.initialize()
        return self._conn  # type: ignore[return-value]

    # -------------------------------------------------------------------
    # FR-2: Track new predictions
    # -------------------------------------------------------------------

    async def track_prediction(
        self, verdict: FinalVerdict, price_at_prediction: float
    ) -> list[PredictionOutcome]:
        """Create PredictionOutcome entries for each configured window."""
        conn = await self._ensure_conn()
        outcomes: list[PredictionOutcome] = []
        now = verdict.timestamp

        analyst_json = json.dumps(verdict.analyst_signals)

        for window in self._windows:
            oid = str(uuid.uuid4())
            outcome = PredictionOutcome(
                outcome_id=oid,
                ticker=verdict.ticker,
                verdict_session_id=verdict.session_id,
                predicted_signal=verdict.final_signal,
                predicted_confidence=verdict.overall_confidence,
                price_at_prediction=price_at_prediction,
                check_window_days=window,
                outcome="pending",
                created_at=now,
            )
            await conn.execute(
                """INSERT INTO prediction_outcomes
                   (outcome_id, ticker, verdict_session_id, predicted_signal,
                    predicted_confidence, price_at_prediction, check_window_days,
                    outcome, analyst_signals_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    oid,
                    verdict.ticker,
                    verdict.session_id,
                    verdict.final_signal,
                    verdict.overall_confidence,
                    price_at_prediction,
                    window,
                    "pending",
                    analyst_json,
                    now.isoformat(),
                ),
            )
            outcomes.append(outcome)

        await conn.commit()
        return outcomes

    # -------------------------------------------------------------------
    # FR-3: Check pending predictions
    # -------------------------------------------------------------------

    async def check_pending_predictions(self) -> list[PredictionOutcome]:
        """Resolve pending predictions whose window has elapsed."""
        conn = await self._ensure_conn()
        now = datetime.now(timezone.utc)

        cursor = await conn.execute(
            """SELECT outcome_id, ticker, verdict_session_id, predicted_signal,
                      predicted_confidence, price_at_prediction, check_window_days,
                      created_at
               FROM prediction_outcomes
               WHERE outcome = 'pending'"""
        )
        rows = await cursor.fetchall()

        resolved: list[PredictionOutcome] = []

        for row in rows:
            oid, ticker, vsid, signal, conf, price_pred, window, created_str = row
            created = datetime.fromisoformat(created_str)
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            check_date = created + timedelta(days=window)
            if now < check_date:
                continue  # Not mature yet

            # Look up price
            try:
                price_now = await self._price_lookup(ticker, check_date)
            except Exception:
                logger.warning("Price lookup failed for %s at +%d days", ticker, window)
                continue

            if price_now is None:
                continue  # Can't resolve yet

            actual_return = (price_now - price_pred) / price_pred
            outcome_str = "correct" if is_signal_correct(signal, actual_return) else "incorrect"

            await conn.execute(
                """UPDATE prediction_outcomes
                   SET outcome = ?, price_at_check = ?, actual_return_pct = ?,
                       checked_at = ?
                   WHERE outcome_id = ?""",
                (outcome_str, price_now, actual_return, now.isoformat(), oid),
            )

            resolved.append(
                PredictionOutcome(
                    outcome_id=oid,
                    ticker=ticker,
                    verdict_session_id=vsid,
                    predicted_signal=signal,
                    predicted_confidence=conf,
                    price_at_prediction=price_pred,
                    price_at_check=price_now,
                    actual_return_pct=actual_return,
                    check_window_days=window,
                    outcome=outcome_str,
                    checked_at=now,
                )
            )

        if resolved:
            await conn.commit()

        return resolved

    # -------------------------------------------------------------------
    # FR-4: Accuracy scorecard
    # -------------------------------------------------------------------

    async def get_accuracy_scorecard(self, ticker: str | None = None) -> AccuracyScorecard:
        """Compute accuracy scorecard, optionally filtered by ticker."""
        conn = await self._ensure_conn()

        if ticker:
            cursor = await conn.execute(
                """SELECT predicted_signal, predicted_confidence, check_window_days,
                          outcome
                   FROM prediction_outcomes WHERE ticker = ?""",
                (ticker,),
            )
        else:
            cursor = await conn.execute(
                """SELECT predicted_signal, predicted_confidence, check_window_days,
                          outcome
                   FROM prediction_outcomes"""
            )

        rows = await cursor.fetchall()

        if not rows:
            return AccuracyScorecard()

        total = len(rows)
        resolved = [r for r in rows if r[3] in ("correct", "incorrect")]
        pending = total - len(resolved)

        # Accuracy by window
        accuracy_by_window: dict[int, float] = {}
        window_counts: dict[int, dict[str, int]] = {}
        for _, _, window, outcome in rows:
            if outcome not in ("correct", "incorrect"):
                continue
            if window not in window_counts:
                window_counts[window] = {"correct": 0, "total": 0}
            window_counts[window]["total"] += 1
            if outcome == "correct":
                window_counts[window]["correct"] += 1

        for w, counts in window_counts.items():
            if counts["total"] > 0:
                accuracy_by_window[w] = counts["correct"] / counts["total"]

        # Accuracy by signal
        accuracy_by_signal: dict[str, float] = {}
        signal_counts: dict[str, dict[str, int]] = {}
        for signal, _, _, outcome in rows:
            if outcome not in ("correct", "incorrect"):
                continue
            if signal not in signal_counts:
                signal_counts[signal] = {"correct": 0, "total": 0}
            signal_counts[signal]["total"] += 1
            if outcome == "correct":
                signal_counts[signal]["correct"] += 1

        for sig, counts in signal_counts.items():
            if counts["total"] > 0:
                accuracy_by_signal[sig] = counts["correct"] / counts["total"]

        # Overall hit rate
        total_resolved = len(resolved)
        correct_count = sum(1 for r in resolved if r[3] == "correct")
        hit_rate = correct_count / total_resolved if total_resolved > 0 else 0.0

        # Confidence calibration (simple: avg confidence of correct vs all)
        conf_calibration = 0.0
        if total_resolved > 0:
            avg_conf = sum(r[1] for r in resolved) / total_resolved
            conf_calibration = min(1.0, hit_rate / max(avg_conf, 0.01))

        return AccuracyScorecard(
            total_predictions=total,
            resolved_predictions=total_resolved,
            pending_predictions=pending,
            accuracy_by_window=accuracy_by_window,
            accuracy_by_signal=accuracy_by_signal,
            hit_rate=hit_rate,
            confidence_calibration=conf_calibration,
        )

    # -------------------------------------------------------------------
    # FR-5: Per-agent accuracy
    # -------------------------------------------------------------------

    async def get_agent_accuracy(self) -> dict[str, AgentAccuracy]:
        """Compute per-agent accuracy from stored analyst_signals."""
        conn = await self._ensure_conn()

        cursor = await conn.execute(
            """SELECT predicted_signal, analyst_signals_json, outcome,
                      predicted_confidence
               FROM prediction_outcomes
               WHERE outcome IN ('correct', 'incorrect')
                 AND analyst_signals_json IS NOT NULL"""
        )
        rows = await cursor.fetchall()

        agent_stats: dict[str, dict] = {}

        for verdict_signal, signals_json, outcome, confidence in rows:
            try:
                analyst_signals = json.loads(signals_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # actual_return direction: if verdict was correct, the predicted direction
            # was right. Each agent that agreed with the verdict direction was also correct.
            verdict_correct = outcome == "correct"

            for agent_name, agent_signal in analyst_signals.items():
                if agent_name not in agent_stats:
                    agent_stats[agent_name] = {
                        "total": 0,
                        "correct": 0,
                        "conf_sum": 0.0,
                    }
                agent_stats[agent_name]["total"] += 1
                agent_stats[agent_name]["conf_sum"] += confidence

                # Agent is correct if it agreed with verdict AND verdict was correct,
                # OR it disagreed with verdict AND verdict was incorrect
                agent_agreed = agent_signal == verdict_signal
                if (agent_agreed and verdict_correct) or (not agent_agreed and not verdict_correct):
                    agent_stats[agent_name]["correct"] += 1

        result: dict[str, AgentAccuracy] = {}
        for name, stats in agent_stats.items():
            total = stats["total"]
            correct = stats["correct"]
            result[name] = AgentAccuracy(
                agent_name=name,
                total_signals=total,
                correct_signals=correct,
                accuracy=correct / total if total > 0 else 0.0,
                avg_confidence=stats["conf_sum"] / total if total > 0 else 0.0,
            )

        return result

    # -------------------------------------------------------------------
    # FR-6: Weight adjustment
    # -------------------------------------------------------------------

    async def recommend_weight_adjustments(self) -> WeightAdjustment:
        """Recommend new signal weights based on agent accuracy."""
        agent_acc = await self.get_agent_accuracy()

        current_weights = dict(DEFAULT_WEIGHTS)
        total_resolved = sum(a.total_signals for a in agent_acc.values())

        # Determine confidence level
        if total_resolved >= 50:
            confidence = "high"
        elif total_resolved >= 20:
            confidence = "medium"
        else:
            confidence = "low"

        agent_accuracies = {name: a.accuracy for name, a in agent_acc.items()}

        if total_resolved < 20:
            return WeightAdjustment(
                current_weights=current_weights,
                recommended_weights={},
                agent_accuracies=agent_accuracies,
                confidence=confidence,
            )

        # Compute recommended weights
        raw_weights: dict[str, float] = {}
        for agent_name, base_weight in current_weights.items():
            acc = agent_accuracies.get(agent_name, 0.5)
            raw_weights[agent_name] = base_weight * (0.5 + acc)

        # Normalize to sum=1.0
        total_raw = sum(raw_weights.values())
        if total_raw > 0:
            recommended = {k: v / total_raw for k, v in raw_weights.items()}
        else:
            recommended = dict(current_weights)

        return WeightAdjustment(
            current_weights=current_weights,
            recommended_weights=recommended,
            agent_accuracies=agent_accuracies,
            confidence=confidence,
        )

    # -------------------------------------------------------------------
    # FR-7: Dashboard summary
    # -------------------------------------------------------------------

    async def get_scorecard_summary(self) -> dict:
        """Combined summary for dashboard rendering."""
        conn = await self._ensure_conn()

        scorecard = await self.get_accuracy_scorecard()
        agent_acc = await self.get_agent_accuracy()
        weight_adj = await self.recommend_weight_adjustments()

        # Recent outcomes
        cursor = await conn.execute(
            """SELECT outcome_id, ticker, verdict_session_id, predicted_signal,
                      predicted_confidence, price_at_prediction, price_at_check,
                      actual_return_pct, check_window_days, outcome, checked_at
               FROM prediction_outcomes
               WHERE outcome != 'pending'
               ORDER BY checked_at DESC
               LIMIT 20"""
        )
        recent_rows = await cursor.fetchall()
        recent_outcomes = [
            {
                "outcome_id": r[0],
                "ticker": r[1],
                "verdict_session_id": r[2],
                "predicted_signal": r[3],
                "predicted_confidence": r[4],
                "price_at_prediction": r[5],
                "price_at_check": r[6],
                "actual_return_pct": r[7],
                "check_window_days": r[8],
                "outcome": r[9],
                "checked_at": r[10],
            }
            for r in recent_rows
        ]

        return {
            "scorecard": scorecard.model_dump(),
            "agent_accuracy": {k: v.model_dump() for k, v in agent_acc.items()},
            "weight_adjustment": weight_adj.model_dump(),
            "recent_outcomes": recent_outcomes,
        }
