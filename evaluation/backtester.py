"""Historical backtesting engine (S14.3).

Evaluates past FinalVerdicts against actual price movements to track
prediction accuracy across configurable time windows.
"""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Callable

from pydantic import BaseModel, Field, field_validator

from config.data_contracts import FinalVerdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BacktestConfig(BaseModel):
    """Configuration for a backtest run (FR-1)."""

    ticker: str
    windows: list[int] = Field(default_factory=lambda: [30, 60, 90])
    min_confidence: float = 0.0
    start_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("min_confidence", mode="before")
    @classmethod
    def clamp_min_confidence(cls, v):
        return max(0.0, min(1.0, float(v)))


class BacktestResult(BaseModel):
    """Result for a single verdict evaluation (FR-2)."""

    ticker: str
    session_id: str
    predicted_signal: str
    predicted_confidence: float
    price_at_prediction: float | None = None
    price_after: dict[int, float | None] = {}
    actual_returns: dict[int, float] = {}
    outcomes: dict[int, str] = {}  # "correct" / "incorrect" / "pending"
    verdict_date: datetime


class BacktestSummary(BaseModel):
    """Aggregated backtest metrics (FR-3)."""

    ticker: str
    total_verdicts: int
    evaluated_verdicts: int
    accuracy_by_window: dict[int, float] = {}
    average_confidence: float = 0.0
    signal_distribution: dict[str, int] = {}
    results: list[BacktestResult] = []


# ---------------------------------------------------------------------------
# Signal correctness (FR-7)
# ---------------------------------------------------------------------------


def is_signal_correct(signal: str, actual_return: float) -> bool:
    """Determine if a predicted signal was correct given the actual return.

    Rules:
    - BUY / STRONG_BUY: correct if actual_return > 0
    - SELL / STRONG_SELL: correct if actual_return < 0
    - HOLD: correct if abs(actual_return) < 0.05
    - Unknown signal: False
    """
    if signal in ("BUY", "STRONG_BUY"):
        return actual_return > 0
    if signal in ("SELL", "STRONG_SELL"):
        return actual_return < 0
    if signal == "HOLD":
        return abs(actual_return) < 0.05
    return False


# Type alias for the price lookup function
PriceLookup = Callable[[str, datetime], float | None]


# ---------------------------------------------------------------------------
# Backtester
# ---------------------------------------------------------------------------


class Backtester:
    """Historical backtesting engine."""

    async def evaluate_verdict(
        self,
        verdict: FinalVerdict,
        price_lookup: PriceLookup,
        windows: list[int] | None = None,
    ) -> BacktestResult:
        """Evaluate a single verdict against actual price data (FR-4)."""
        if windows is None:
            windows = [30, 60, 90]

        pred_date = verdict.timestamp
        price_at_pred: float | None = None
        price_after: dict[int, float | None] = {}
        actual_returns: dict[int, float] = {}
        outcomes: dict[int, str] = {}

        # Get price at prediction time
        try:
            price_at_pred = await price_lookup(verdict.ticker, pred_date)
        except Exception:
            logger.warning("Price lookup failed for %s at prediction date", verdict.ticker)
            price_at_pred = None

        for w in windows:
            future_date = pred_date + timedelta(days=w)

            if price_at_pred is None:
                price_after[w] = None
                outcomes[w] = "pending"
                continue

            try:
                future_price = await price_lookup(verdict.ticker, future_date)
            except Exception:
                logger.warning("Price lookup failed for %s at +%d days", verdict.ticker, w)
                future_price = None

            if future_price is None:
                price_after[w] = None
                outcomes[w] = "pending"
            else:
                price_after[w] = future_price
                ret = (future_price - price_at_pred) / price_at_pred
                actual_returns[w] = ret
                outcomes[w] = (
                    "correct" if is_signal_correct(verdict.final_signal, ret) else "incorrect"
                )

        return BacktestResult(
            ticker=verdict.ticker,
            session_id=verdict.session_id,
            predicted_signal=verdict.final_signal,
            predicted_confidence=verdict.overall_confidence,
            price_at_prediction=price_at_pred,
            price_after=price_after,
            actual_returns=actual_returns,
            outcomes=outcomes,
            verdict_date=pred_date,
        )

    async def run_backtest(
        self,
        config: BacktestConfig,
        history_retriever,
        price_lookup: PriceLookup,
    ) -> BacktestSummary:
        """Run a full backtest for a ticker (FR-5)."""
        try:
            verdicts = await history_retriever.get_ticker_history(config.ticker, limit=200)
        except Exception:
            logger.exception("Failed to fetch history for %s", config.ticker)
            verdicts = []

        # Filter by confidence
        if config.min_confidence > 0:
            verdicts = [v for v in verdicts if v.overall_confidence >= config.min_confidence]

        # Filter by date range
        if config.start_date:
            verdicts = [v for v in verdicts if v.timestamp >= config.start_date]
        if config.end_date:
            verdicts = [v for v in verdicts if v.timestamp <= config.end_date]

        if not verdicts:
            return BacktestSummary(
                ticker=config.ticker,
                total_verdicts=0,
                evaluated_verdicts=0,
                accuracy_by_window={},
                average_confidence=0.0,
                signal_distribution={},
                results=[],
            )

        # Evaluate each verdict
        results: list[BacktestResult] = []
        for v in verdicts:
            try:
                result = await self.evaluate_verdict(v, price_lookup, config.windows)
                results.append(result)
            except Exception:
                logger.exception("Failed to evaluate verdict %s", v.session_id)

        # Compute summary
        total = len(results)
        signal_dist = dict(Counter(r.predicted_signal for r in results))
        avg_conf = sum(r.predicted_confidence for r in results) / total if total else 0.0

        # Accuracy per window
        accuracy_by_window: dict[int, float] = {}
        evaluated = 0
        for w in config.windows:
            correct = 0
            total_w = 0
            for r in results:
                outcome = r.outcomes.get(w)
                if outcome in ("correct", "incorrect"):
                    total_w += 1
                    if outcome == "correct":
                        correct += 1
            if total_w > 0:
                accuracy_by_window[w] = correct / total_w
                evaluated = max(evaluated, total_w)

        return BacktestSummary(
            ticker=config.ticker,
            total_verdicts=total,
            evaluated_verdicts=evaluated,
            accuracy_by_window=accuracy_by_window,
            average_confidence=avg_conf,
            signal_distribution=signal_dist,
            results=results,
        )

    async def run_multi_ticker(
        self,
        tickers: list[str],
        history_retriever,
        price_lookup: PriceLookup,
        windows: list[int] | None = None,
    ) -> dict[str, BacktestSummary]:
        """Run backtests across multiple tickers (FR-6)."""
        if not tickers:
            return {}

        if windows is None:
            windows = [30, 60, 90]

        results: dict[str, BacktestSummary] = {}

        async def _run_one(ticker: str):
            try:
                config = BacktestConfig(ticker=ticker, windows=windows)
                summary = await self.run_backtest(config, history_retriever, price_lookup)
                results[ticker] = summary
            except Exception:
                logger.exception("Backtest failed for %s", ticker)

        await asyncio.gather(*[_run_one(t) for t in tickers])
        return results
