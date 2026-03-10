"""Tests for evaluation/backtester.py (S14.3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.data_contracts import FinalVerdict
from evaluation.backtester import (
    BacktestConfig,
    Backtester,
    BacktestResult,
    BacktestSummary,
    is_signal_correct,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_verdict(
    ticker: str = "AAPL",
    signal: str = "BUY",
    confidence: float = 0.65,
    session_id: str = "sess-1",
    days_ago: int = 60,
) -> FinalVerdict:
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        analyst_signals={"valuation_scout": signal},
        session_id=session_id,
        timestamp=ts,
    )


def _make_price_lookup(prices: dict[str, dict[str, float | None]]):
    """Create a mock async price lookup.

    prices: {ticker: {iso_date_str: price}} -- date keys are matched by date only.
    """

    async def lookup(ticker: str, date: datetime) -> float | None:
        ticker_prices = prices.get(ticker, {})
        date_str = date.strftime("%Y-%m-%d")
        return ticker_prices.get(date_str)

    return lookup


# ---------------------------------------------------------------------------
# FR-1: BacktestConfig
# ---------------------------------------------------------------------------


class TestBacktestConfig:
    def test_defaults(self):
        cfg = BacktestConfig(ticker="AAPL")
        assert cfg.ticker == "AAPL"
        assert cfg.windows == [30, 60, 90]
        assert cfg.min_confidence == 0.0
        assert cfg.start_date is None
        assert cfg.end_date is None

    def test_custom_windows(self):
        cfg = BacktestConfig(ticker="TSLA", windows=[7, 14])
        assert cfg.windows == [7, 14]

    def test_min_confidence_clamped_high(self):
        cfg = BacktestConfig(ticker="AAPL", min_confidence=1.5)
        assert cfg.min_confidence == 1.0

    def test_min_confidence_clamped_low(self):
        cfg = BacktestConfig(ticker="AAPL", min_confidence=-0.5)
        assert cfg.min_confidence == 0.0


# ---------------------------------------------------------------------------
# FR-2: BacktestResult
# ---------------------------------------------------------------------------


class TestBacktestResult:
    def test_valid(self):
        result = BacktestResult(
            ticker="AAPL",
            session_id="sess-1",
            predicted_signal="BUY",
            predicted_confidence=0.65,
            price_at_prediction=150.0,
            price_after={30: 160.0},
            actual_returns={30: 0.0667},
            outcomes={30: "correct"},
            verdict_date=datetime.now(timezone.utc),
        )
        assert result.ticker == "AAPL"
        assert result.outcomes[30] == "correct"

    def test_pending_outcome(self):
        result = BacktestResult(
            ticker="AAPL",
            session_id="sess-1",
            predicted_signal="BUY",
            predicted_confidence=0.65,
            price_at_prediction=150.0,
            price_after={},
            actual_returns={},
            outcomes={30: "pending"},
            verdict_date=datetime.now(timezone.utc),
        )
        assert result.outcomes[30] == "pending"


# ---------------------------------------------------------------------------
# FR-3: BacktestSummary
# ---------------------------------------------------------------------------


class TestBacktestSummary:
    def test_valid(self):
        summary = BacktestSummary(
            ticker="AAPL",
            total_verdicts=5,
            evaluated_verdicts=3,
            accuracy_by_window={30: 0.67, 60: 0.50},
            average_confidence=0.65,
            signal_distribution={"BUY": 3, "SELL": 2},
            results=[],
        )
        assert summary.total_verdicts == 5
        assert summary.accuracy_by_window[30] == 0.67

    def test_no_evaluated(self):
        summary = BacktestSummary(
            ticker="AAPL",
            total_verdicts=0,
            evaluated_verdicts=0,
            accuracy_by_window={},
            average_confidence=0.0,
            signal_distribution={},
            results=[],
        )
        assert summary.accuracy_by_window == {}


# ---------------------------------------------------------------------------
# FR-7: is_signal_correct
# ---------------------------------------------------------------------------


class TestIsSignalCorrect:
    def test_buy_up(self):
        assert is_signal_correct("BUY", 0.10) is True

    def test_buy_down(self):
        assert is_signal_correct("BUY", -0.05) is False

    def test_sell_down(self):
        assert is_signal_correct("SELL", -0.10) is True

    def test_sell_up(self):
        assert is_signal_correct("SELL", 0.05) is False

    def test_hold_small(self):
        assert is_signal_correct("HOLD", 0.03) is True

    def test_hold_negative_small(self):
        assert is_signal_correct("HOLD", -0.04) is True

    def test_hold_large(self):
        assert is_signal_correct("HOLD", 0.10) is False

    def test_strong_buy(self):
        assert is_signal_correct("STRONG_BUY", 0.15) is True

    def test_strong_buy_down(self):
        assert is_signal_correct("STRONG_BUY", -0.05) is False

    def test_strong_sell(self):
        assert is_signal_correct("STRONG_SELL", -0.15) is True

    def test_strong_sell_up(self):
        assert is_signal_correct("STRONG_SELL", 0.05) is False

    def test_unknown_signal(self):
        assert is_signal_correct("UNKNOWN", 0.10) is False

    def test_buy_zero_return(self):
        assert is_signal_correct("BUY", 0.0) is False

    def test_sell_zero_return(self):
        assert is_signal_correct("SELL", 0.0) is False

    def test_hold_zero_return(self):
        assert is_signal_correct("HOLD", 0.0) is True


# ---------------------------------------------------------------------------
# FR-4: evaluate_verdict
# ---------------------------------------------------------------------------


class TestEvaluateVerdict:
    @pytest.mark.asyncio
    async def test_all_windows(self):
        verdict = _make_verdict(signal="BUY", confidence=0.65, days_ago=100)
        pred_date = verdict.timestamp
        prices = {
            "AAPL": {
                pred_date.strftime("%Y-%m-%d"): 100.0,
                (pred_date + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
                (pred_date + timedelta(days=60)).strftime("%Y-%m-%d"): 105.0,
                (pred_date + timedelta(days=90)).strftime("%Y-%m-%d"): 95.0,
            }
        }
        lookup = _make_price_lookup(prices)
        bt = Backtester()
        result = await bt.evaluate_verdict(verdict, lookup, windows=[30, 60, 90])

        assert result.ticker == "AAPL"
        assert result.outcomes[30] == "correct"  # BUY + up
        assert result.outcomes[60] == "correct"  # BUY + up
        assert result.outcomes[90] == "incorrect"  # BUY + down
        assert result.price_at_prediction == 100.0
        assert abs(result.actual_returns[30] - 0.10) < 0.001

    @pytest.mark.asyncio
    async def test_missing_price(self):
        verdict = _make_verdict(signal="SELL", days_ago=100)
        # Only prediction date price, no future prices
        pred_date = verdict.timestamp
        prices = {
            "AAPL": {
                pred_date.strftime("%Y-%m-%d"): 100.0,
            }
        }
        lookup = _make_price_lookup(prices)
        bt = Backtester()
        result = await bt.evaluate_verdict(verdict, lookup, windows=[30])
        assert result.outcomes[30] == "pending"

    @pytest.mark.asyncio
    async def test_missing_prediction_price(self):
        """If we can't get the price at prediction time, all outcomes are pending."""
        verdict = _make_verdict(signal="BUY", days_ago=100)
        lookup = _make_price_lookup({})  # No prices at all
        bt = Backtester()
        result = await bt.evaluate_verdict(verdict, lookup, windows=[30])
        assert result.outcomes[30] == "pending"
        assert result.price_at_prediction is None


# ---------------------------------------------------------------------------
# FR-5: run_backtest
# ---------------------------------------------------------------------------


class TestRunBacktest:
    @pytest.mark.asyncio
    async def test_basic(self):
        v1 = _make_verdict(signal="BUY", confidence=0.65, session_id="s1", days_ago=100)
        v2 = _make_verdict(signal="SELL", confidence=0.70, session_id="s2", days_ago=80)

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(return_value=[v1, v2])

        pred1 = v1.timestamp
        pred2 = v2.timestamp
        prices = {
            "AAPL": {
                pred1.strftime("%Y-%m-%d"): 100.0,
                (pred1 + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
                pred2.strftime("%Y-%m-%d"): 120.0,
                (pred2 + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
            }
        }
        lookup = _make_price_lookup(prices)

        bt = Backtester()
        config = BacktestConfig(ticker="AAPL", windows=[30])
        summary = await bt.run_backtest(config, mock_retriever, lookup)

        assert summary.total_verdicts == 2
        assert summary.evaluated_verdicts == 2
        assert len(summary.results) == 2
        assert summary.accuracy_by_window[30] == 1.0  # Both correct

    @pytest.mark.asyncio
    async def test_confidence_filter(self):
        v1 = _make_verdict(signal="BUY", confidence=0.30, session_id="s1", days_ago=100)
        v2 = _make_verdict(signal="BUY", confidence=0.70, session_id="s2", days_ago=80)

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(return_value=[v1, v2])

        pred2 = v2.timestamp
        prices = {
            "AAPL": {
                pred2.strftime("%Y-%m-%d"): 100.0,
                (pred2 + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
            }
        }
        lookup = _make_price_lookup(prices)

        bt = Backtester()
        config = BacktestConfig(ticker="AAPL", windows=[30], min_confidence=0.50)
        summary = await bt.run_backtest(config, mock_retriever, lookup)

        assert summary.total_verdicts == 1  # v1 filtered out

    @pytest.mark.asyncio
    async def test_date_filter(self):
        now = datetime.now(timezone.utc)
        v1 = _make_verdict(signal="BUY", session_id="s1", days_ago=200)
        v2 = _make_verdict(signal="BUY", session_id="s2", days_ago=50)

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(return_value=[v1, v2])

        pred2 = v2.timestamp
        prices = {
            "AAPL": {
                pred2.strftime("%Y-%m-%d"): 100.0,
                (pred2 + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
            }
        }
        lookup = _make_price_lookup(prices)

        bt = Backtester()
        config = BacktestConfig(
            ticker="AAPL",
            windows=[30],
            start_date=now - timedelta(days=100),
        )
        summary = await bt.run_backtest(config, mock_retriever, lookup)

        assert summary.total_verdicts == 1  # v1 filtered out (too old)

    @pytest.mark.asyncio
    async def test_no_verdicts(self):
        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(return_value=[])

        lookup = _make_price_lookup({})
        bt = Backtester()
        config = BacktestConfig(ticker="AAPL", windows=[30])
        summary = await bt.run_backtest(config, mock_retriever, lookup)

        assert summary.total_verdicts == 0
        assert summary.evaluated_verdicts == 0
        assert summary.accuracy_by_window == {}

    @pytest.mark.asyncio
    async def test_price_lookup_failure(self):
        v1 = _make_verdict(signal="BUY", session_id="s1", days_ago=100)

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(return_value=[v1])

        async def failing_lookup(ticker, date):
            raise ConnectionError("API down")

        bt = Backtester()
        config = BacktestConfig(ticker="AAPL", windows=[30])
        summary = await bt.run_backtest(config, mock_retriever, failing_lookup)

        # Should not crash; verdict result has pending outcomes
        assert summary.total_verdicts == 1
        assert len(summary.results) == 1


# ---------------------------------------------------------------------------
# FR-6: run_multi_ticker
# ---------------------------------------------------------------------------


class TestRunMultiTicker:
    @pytest.mark.asyncio
    async def test_multi_ticker(self):
        v_aapl = _make_verdict(ticker="AAPL", signal="BUY", session_id="s1", days_ago=100)
        v_tsla = _make_verdict(ticker="TSLA", signal="SELL", session_id="s2", days_ago=100)

        async def mock_history(ticker, limit=50, offset=0):
            if ticker == "AAPL":
                return [v_aapl]
            elif ticker == "TSLA":
                return [v_tsla]
            return []

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(side_effect=mock_history)

        pred_aapl = v_aapl.timestamp
        pred_tsla = v_tsla.timestamp
        prices = {
            "AAPL": {
                pred_aapl.strftime("%Y-%m-%d"): 100.0,
                (pred_aapl + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
            },
            "TSLA": {
                pred_tsla.strftime("%Y-%m-%d"): 200.0,
                (pred_tsla + timedelta(days=30)).strftime("%Y-%m-%d"): 180.0,
            },
        }
        lookup = _make_price_lookup(prices)

        bt = Backtester()
        results = await bt.run_multi_ticker(["AAPL", "TSLA"], mock_retriever, lookup, windows=[30])

        assert "AAPL" in results
        assert "TSLA" in results
        assert results["AAPL"].total_verdicts == 1
        assert results["TSLA"].total_verdicts == 1

    @pytest.mark.asyncio
    async def test_empty_list(self):
        bt = Backtester()
        mock_retriever = MagicMock()
        lookup = _make_price_lookup({})
        results = await bt.run_multi_ticker([], mock_retriever, lookup)
        assert results == {}

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        v_aapl = _make_verdict(ticker="AAPL", signal="BUY", session_id="s1", days_ago=100)

        call_count = 0

        async def mock_history(ticker, limit=50, offset=0):
            nonlocal call_count
            call_count += 1
            if ticker == "FAIL":
                raise RuntimeError("DB error")
            return [v_aapl] if ticker == "AAPL" else []

        mock_retriever = MagicMock()
        mock_retriever.get_ticker_history = AsyncMock(side_effect=mock_history)

        pred_aapl = v_aapl.timestamp
        prices = {
            "AAPL": {
                pred_aapl.strftime("%Y-%m-%d"): 100.0,
                (pred_aapl + timedelta(days=30)).strftime("%Y-%m-%d"): 110.0,
            },
        }
        lookup = _make_price_lookup(prices)

        bt = Backtester()
        results = await bt.run_multi_ticker(["AAPL", "FAIL"], mock_retriever, lookup, windows=[30])

        # AAPL succeeds, FAIL is skipped (not in results or has empty summary)
        assert "AAPL" in results
        assert results["AAPL"].total_verdicts == 1
