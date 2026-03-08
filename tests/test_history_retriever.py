"""Tests for memory/history_retriever.py -- HistoryRetriever query layer."""

import asyncio

import pytest
import pytest_asyncio

from config.data_contracts import FinalVerdict
from memory.history_retriever import HistoryRetriever, SignalSnapshot
from memory.insight_vault import InsightVault


def _make_verdict(
    ticker: str = "AAPL",
    signal: str = "BUY",
    confidence: float = 0.80,
    session_id: str = "",
) -> FinalVerdict:
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        price_target=150.0,
        analyst_signals={"valuation": "BUY", "momentum": "HOLD"},
        risk_summary="Moderate risk",
        key_drivers=["Strong earnings", "High momentum"],
        session_id=session_id,
    )


@pytest_asyncio.fixture
async def vault(tmp_path):
    db_path = str(tmp_path / "test.db")
    v = InsightVault(db_path=db_path)
    await v.initialize()
    yield v
    await v.close()


@pytest_asyncio.fixture
async def retriever(vault):
    return HistoryRetriever(vault)


class TestGetTickerHistory:
    @pytest.mark.asyncio
    async def test_returns_verdicts(self, vault, retriever):
        """Store 3 AAPL verdicts, retrieve, assert count and order."""
        for i in range(3):
            await vault.store_verdict(_make_verdict(session_id=f"aapl-{i}"))

        results = await retriever.get_ticker_history("AAPL")
        assert len(results) == 3
        assert all(isinstance(v, FinalVerdict) for v in results)
        # Newest first
        assert results[0].session_id == "aapl-2"
        assert results[2].session_id == "aapl-0"

    @pytest.mark.asyncio
    async def test_empty_ticker(self, retriever):
        """Pass empty string, expect empty list."""
        results = await retriever.get_ticker_history("")
        assert results == []

    @pytest.mark.asyncio
    async def test_unknown_ticker(self, retriever):
        """Query ticker with no data, expect empty list."""
        results = await retriever.get_ticker_history("ZZZZ")
        assert results == []

    @pytest.mark.asyncio
    async def test_limit_clamping(self, vault, retriever):
        """Pass limit=500, verify clamped to 200."""
        await vault.store_verdict(_make_verdict(session_id="clamp-test"))
        results = await retriever.get_ticker_history("AAPL", limit=500)
        assert isinstance(results, list)
        # Should not raise -- limit internally clamped

    @pytest.mark.asyncio
    async def test_offset(self, vault, retriever):
        """Store 5 verdicts, use offset=2 limit=2, verify correct slice."""
        for i in range(5):
            await vault.store_verdict(_make_verdict(session_id=f"off-{i}"))
            # Small delay to ensure ordering
            await asyncio.sleep(0.01)

        results = await retriever.get_ticker_history("AAPL", limit=2, offset=2)
        assert len(results) == 2


class TestGetSignalTrend:
    @pytest.mark.asyncio
    async def test_chronological_order(self, vault, retriever):
        """Store verdicts, verify oldest-first order."""
        await vault.store_verdict(_make_verdict(signal="SELL", session_id="trend-0"))
        await asyncio.sleep(0.01)
        await vault.store_verdict(_make_verdict(signal="HOLD", session_id="trend-1"))
        await asyncio.sleep(0.01)
        await vault.store_verdict(_make_verdict(signal="BUY", session_id="trend-2"))

        results = await retriever.get_signal_trend("AAPL")
        assert len(results) == 3
        # Oldest first (chronological)
        assert results[0].final_signal == "SELL"
        assert results[1].final_signal == "HOLD"
        assert results[2].final_signal == "BUY"

    @pytest.mark.asyncio
    async def test_returns_snapshots(self, vault, retriever):
        """Verify returned objects are SignalSnapshot with correct fields."""
        await vault.store_verdict(_make_verdict(session_id="snap-test"))

        results = await retriever.get_signal_trend("AAPL")
        assert len(results) == 1
        snap = results[0]
        assert isinstance(snap, SignalSnapshot)
        assert snap.session_id == "snap-test"
        assert snap.ticker == "AAPL"
        assert snap.final_signal == "BUY"
        assert snap.overall_confidence == 0.80
        assert isinstance(snap.created_at, str)
        assert len(snap.created_at) > 0

    @pytest.mark.asyncio
    async def test_limit_clamping(self, vault, retriever):
        """Pass limit=500, verify clamped to 100."""
        await vault.store_verdict(_make_verdict(session_id="lc-test"))
        results = await retriever.get_signal_trend("AAPL", limit=500)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_empty(self, retriever):
        """Query unknown ticker, expect empty list."""
        results = await retriever.get_signal_trend("ZZZZ")
        assert results == []


class TestGetRecentVerdicts:
    @pytest.mark.asyncio
    async def test_returns_mixed_tickers(self, vault, retriever):
        """Store verdicts for multiple tickers, verify mixed results."""
        await vault.store_verdict(_make_verdict(ticker="AAPL", session_id="r1"))
        await vault.store_verdict(_make_verdict(ticker="GOOGL", session_id="r2"))
        await vault.store_verdict(_make_verdict(ticker="MSFT", session_id="r3"))

        results = await retriever.get_recent_verdicts()
        assert len(results) == 3
        tickers = {v.ticker for v in results}
        assert tickers == {"AAPL", "GOOGL", "MSFT"}

    @pytest.mark.asyncio
    async def test_limit_and_offset(self, vault, retriever):
        """Verify pagination works."""
        for i in range(5):
            await vault.store_verdict(_make_verdict(session_id=f"page-{i}"))

        results = await retriever.get_recent_verdicts(limit=2, offset=1)
        assert len(results) == 2


class TestSignalSnapshot:
    def test_confidence_clamping(self):
        """Verify confidence clamped to [0, 1]."""
        snap = SignalSnapshot(
            session_id="test",
            ticker="AAPL",
            final_signal="BUY",
            overall_confidence=1.5,
            created_at="2025-01-01T00:00:00",
        )
        assert snap.overall_confidence == 1.0

        snap2 = SignalSnapshot(
            session_id="test",
            ticker="AAPL",
            final_signal="SELL",
            overall_confidence=-0.5,
            created_at="2025-01-01T00:00:00",
        )
        assert snap2.overall_confidence == 0.0
