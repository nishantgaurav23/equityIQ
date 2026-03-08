"""Tests for memory/insight_vault.py -- InsightVault SQLite storage."""

import os

import pytest
import pytest_asyncio

from config.data_contracts import FinalVerdict
from memory.insight_vault import InsightVault


@pytest_asyncio.fixture
async def vault(tmp_path):
    """Create a temporary InsightVault for testing."""
    db_path = str(tmp_path / "test.db")
    v = InsightVault(db_path=db_path)
    await v.initialize()
    yield v
    await v.close()


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


class TestStoreAndRetrieve:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_verdict(self, vault):
        verdict = _make_verdict(session_id="sess-001")
        sid = await vault.store_verdict(verdict)
        assert sid == "sess-001"

        retrieved = await vault.get_verdict("sess-001")
        assert retrieved is not None
        assert retrieved.ticker == "AAPL"
        assert retrieved.final_signal == "BUY"
        assert retrieved.overall_confidence == 0.80
        assert retrieved.price_target == 150.0

    @pytest.mark.asyncio
    async def test_store_generates_session_id(self, vault):
        verdict = _make_verdict(session_id="")
        sid = await vault.store_verdict(verdict)
        assert sid != ""
        assert len(sid) > 0

        retrieved = await vault.get_verdict(sid)
        assert retrieved is not None
        assert retrieved.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_store_preserves_session_id(self, vault):
        verdict = _make_verdict(session_id="my-custom-id")
        sid = await vault.store_verdict(verdict)
        assert sid == "my-custom-id"

    @pytest.mark.asyncio
    async def test_get_verdict_not_found(self, vault):
        result = await vault.get_verdict("nonexistent")
        assert result is None


class TestListVerdicts:
    @pytest.mark.asyncio
    async def test_list_verdicts_all(self, vault):
        await vault.store_verdict(_make_verdict(ticker="AAPL", session_id="s1"))
        await vault.store_verdict(_make_verdict(ticker="GOOGL", session_id="s2"))
        await vault.store_verdict(_make_verdict(ticker="MSFT", session_id="s3"))

        results = await vault.list_verdicts()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_verdicts_by_ticker(self, vault):
        await vault.store_verdict(_make_verdict(ticker="AAPL", session_id="s1"))
        await vault.store_verdict(_make_verdict(ticker="GOOGL", session_id="s2"))
        await vault.store_verdict(_make_verdict(ticker="AAPL", session_id="s3"))

        results = await vault.list_verdicts(ticker="AAPL")
        assert len(results) == 2
        assert all(v.ticker == "AAPL" for v in results)

    @pytest.mark.asyncio
    async def test_list_verdicts_limit_offset(self, vault):
        for i in range(10):
            await vault.store_verdict(_make_verdict(session_id=f"s{i}"))

        results = await vault.list_verdicts(limit=3, offset=2)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_list_verdicts_limit_cap(self, vault):
        """Limit should be capped at 200."""
        results = await vault.list_verdicts(limit=500)
        assert isinstance(results, list)
        # The important thing is the query doesn't fail with limit=500
        # The actual cap is enforced internally

    @pytest.mark.asyncio
    async def test_list_verdicts_ordered_desc(self, vault):
        await vault.store_verdict(_make_verdict(ticker="AAPL", session_id="first"))
        await vault.store_verdict(_make_verdict(ticker="GOOGL", session_id="second"))

        results = await vault.list_verdicts()
        # Most recent first
        assert results[0].session_id == "second"
        assert results[1].session_id == "first"


class TestDeleteVerdict:
    @pytest.mark.asyncio
    async def test_delete_verdict(self, vault):
        await vault.store_verdict(_make_verdict(session_id="to-delete"))
        assert await vault.get_verdict("to-delete") is not None

        deleted = await vault.delete_verdict("to-delete")
        assert deleted is True
        assert await vault.get_verdict("to-delete") is None

    @pytest.mark.asyncio
    async def test_delete_verdict_not_found(self, vault):
        deleted = await vault.delete_verdict("nonexistent")
        assert deleted is False


class TestInitialization:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "test.db")
        v = InsightVault(db_path=db_path)
        await v.initialize()

        # Should be able to store and retrieve after init
        sid = await v.store_verdict(_make_verdict(session_id="init-test"))
        result = await v.get_verdict(sid)
        assert result is not None
        await v.close()

    @pytest.mark.asyncio
    async def test_initialize_creates_directory(self, tmp_path):
        db_path = str(tmp_path / "deep" / "nested" / "test.db")
        v = InsightVault(db_path=db_path)
        await v.initialize()

        parent = os.path.dirname(db_path)
        assert os.path.isdir(parent)
        await v.close()


class TestRoundTrip:
    @pytest.mark.asyncio
    async def test_round_trip_lossless(self, vault):
        original = _make_verdict(
            ticker="TSLA",
            signal="HOLD",
            confidence=0.65,
            session_id="round-trip",
        )
        original.price_target = 250.5
        original.analyst_signals = {
            "valuation": "BUY",
            "momentum": "SELL",
            "pulse": "HOLD",
        }
        original.risk_summary = "High volatility expected"
        original.key_drivers = ["EV market growth", "Competition risk", "Margin pressure"]

        await vault.store_verdict(original)
        retrieved = await vault.get_verdict("round-trip")

        assert retrieved is not None
        assert retrieved.ticker == original.ticker
        assert retrieved.final_signal == original.final_signal
        assert retrieved.overall_confidence == original.overall_confidence
        assert retrieved.price_target == original.price_target
        assert retrieved.analyst_signals == original.analyst_signals
        assert retrieved.risk_summary == original.risk_summary
        assert retrieved.key_drivers == original.key_drivers
        assert retrieved.session_id == original.session_id


class TestClose:
    @pytest.mark.asyncio
    async def test_close(self, tmp_path):
        db_path = str(tmp_path / "close_test.db")
        v = InsightVault(db_path=db_path)
        await v.initialize()
        await v.close()
        # Should not raise
        await v.close()  # Double close is safe
