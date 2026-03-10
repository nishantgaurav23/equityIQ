"""Tests for memory/vertex_memory.py -- VertexMemoryBank (S16.1)."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio

from config.data_contracts import (
    ConversationEntry,
    PredictionOutcome,
    UserPreference,
)
from memory.vertex_memory import VertexMemoryBank, get_memory_bank


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestUserPreference:
    def test_defaults(self):
        pref = UserPreference(user_id="u1", updated_at=_utcnow())
        assert pref.user_id == "u1"
        assert pref.favorite_tickers == []
        assert pref.risk_tolerance == "moderate"
        assert pref.preferred_agents == []
        assert pref.notification_enabled is False

    def test_custom_values(self):
        pref = UserPreference(
            user_id="u2",
            favorite_tickers=["AAPL", "MSFT"],
            risk_tolerance="aggressive",
            preferred_agents=["valuation_scout"],
            notification_enabled=True,
            updated_at=_utcnow(),
        )
        assert pref.favorite_tickers == ["AAPL", "MSFT"]
        assert pref.risk_tolerance == "aggressive"

    def test_invalid_risk_tolerance(self):
        with pytest.raises(Exception):
            UserPreference(user_id="u1", risk_tolerance="yolo", updated_at=_utcnow())


class TestConversationEntry:
    def test_basic(self):
        entry = ConversationEntry(
            entry_id="e1",
            user_id="u1",
            session_id="s1",
            role="user",
            content="Analyze AAPL",
            created_at=_utcnow(),
        )
        assert entry.role == "user"
        assert entry.ticker is None
        assert entry.verdict_session_id is None

    def test_with_ticker(self):
        entry = ConversationEntry(
            entry_id="e2",
            user_id="u1",
            session_id="s1",
            role="assistant",
            content="AAPL is a BUY",
            ticker="AAPL",
            verdict_session_id="vs1",
            created_at=_utcnow(),
        )
        assert entry.ticker == "AAPL"
        assert entry.verdict_session_id == "vs1"

    def test_invalid_role(self):
        with pytest.raises(Exception):
            ConversationEntry(
                entry_id="e1",
                user_id="u1",
                session_id="s1",
                role="system",
                content="test",
                created_at=_utcnow(),
            )


class TestPredictionOutcome:
    def test_defaults(self):
        pred = PredictionOutcome(
            outcome_id="o1",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=0.85,
            price_at_prediction=150.0,
            created_at=_utcnow(),
        )
        assert pred.outcome == "pending"
        assert pred.check_window_days == 30
        assert pred.price_at_check is None
        assert pred.actual_return_pct is None

    def test_confidence_clamped(self):
        pred = PredictionOutcome(
            outcome_id="o1",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=1.5,
            price_at_prediction=150.0,
            created_at=_utcnow(),
        )
        assert pred.predicted_confidence == 1.0

    def test_confidence_clamped_negative(self):
        pred = PredictionOutcome(
            outcome_id="o1",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=-0.5,
            price_at_prediction=150.0,
            created_at=_utcnow(),
        )
        assert pred.predicted_confidence == 0.0

    def test_invalid_outcome(self):
        with pytest.raises(Exception):
            PredictionOutcome(
                outcome_id="o1",
                ticker="AAPL",
                verdict_session_id="vs1",
                predicted_signal="BUY",
                predicted_confidence=0.8,
                price_at_prediction=150.0,
                outcome="unknown",
                created_at=_utcnow(),
            )


# ---------------------------------------------------------------------------
# VertexMemoryBank tests (SQLite in-memory)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def memory_bank():
    """Create an in-memory VertexMemoryBank for testing."""
    bank = VertexMemoryBank(db_path=":memory:")
    await bank.initialize()
    yield bank
    await bank.close()


class TestInitializeAndClose:
    @pytest.mark.asyncio
    async def test_initialize_creates_tables(self, memory_bank):
        # If we got here, initialization worked. Verify by storing data.
        prefs = UserPreference(user_id="u1", updated_at=_utcnow())
        await memory_bank.update_preferences(prefs)
        result = await memory_bank.get_preferences("u1")
        assert result is not None

    @pytest.mark.asyncio
    async def test_close_clears_connection(self, memory_bank):
        await memory_bank.close()
        assert memory_bank._conn is None

    @pytest.mark.asyncio
    async def test_double_close(self, memory_bank):
        await memory_bank.close()
        await memory_bank.close()  # Should not raise


class TestUserPreferences:
    @pytest.mark.asyncio
    async def test_get_nonexistent(self, memory_bank):
        result = await memory_bank.get_preferences("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_and_get(self, memory_bank):
        prefs = UserPreference(
            user_id="u1",
            favorite_tickers=["AAPL", "GOOGL"],
            risk_tolerance="aggressive",
            updated_at=_utcnow(),
        )
        await memory_bank.update_preferences(prefs)
        result = await memory_bank.get_preferences("u1")
        assert result is not None
        assert result.user_id == "u1"
        assert result.favorite_tickers == ["AAPL", "GOOGL"]
        assert result.risk_tolerance == "aggressive"

    @pytest.mark.asyncio
    async def test_update_upsert(self, memory_bank):
        prefs1 = UserPreference(user_id="u1", favorite_tickers=["AAPL"], updated_at=_utcnow())
        await memory_bank.update_preferences(prefs1)

        prefs2 = UserPreference(
            user_id="u1", favorite_tickers=["AAPL", "MSFT"], updated_at=_utcnow()
        )
        await memory_bank.update_preferences(prefs2)

        result = await memory_bank.get_preferences("u1")
        assert result.favorite_tickers == ["AAPL", "MSFT"]


class TestConversationStorage:
    @pytest.mark.asyncio
    async def test_store_and_get_by_session(self, memory_bank):
        entry1 = ConversationEntry(
            entry_id="e1",
            user_id="u1",
            session_id="s1",
            role="user",
            content="Analyze AAPL",
            ticker="AAPL",
            created_at=_utcnow(),
        )
        entry2 = ConversationEntry(
            entry_id="e2",
            user_id="u1",
            session_id="s1",
            role="assistant",
            content="AAPL is a BUY",
            ticker="AAPL",
            verdict_session_id="vs1",
            created_at=_utcnow(),
        )
        await memory_bank.store_conversation_entry(entry1)
        await memory_bank.store_conversation_entry(entry2)

        entries = await memory_bank.get_conversation("s1")
        assert len(entries) == 2
        assert entries[0].role == "user"
        assert entries[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_get_empty_conversation(self, memory_bank):
        entries = await memory_bank.get_conversation("nonexistent")
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_user_conversations(self, memory_bank):
        for i in range(3):
            entry = ConversationEntry(
                entry_id=f"e{i}",
                user_id="u1",
                session_id=f"s{i}",
                role="user",
                content=f"Message {i}",
                created_at=_utcnow(),
            )
            await memory_bank.store_conversation_entry(entry)

        # Different user
        other = ConversationEntry(
            entry_id="e_other",
            user_id="u2",
            session_id="s_other",
            role="user",
            content="Other user",
            created_at=_utcnow(),
        )
        await memory_bank.store_conversation_entry(other)

        entries = await memory_bank.get_user_conversations("u1")
        assert len(entries) == 3
        assert all(e.user_id == "u1" for e in entries)

    @pytest.mark.asyncio
    async def test_conversation_limit(self, memory_bank):
        for i in range(10):
            entry = ConversationEntry(
                entry_id=f"e{i}",
                user_id="u1",
                session_id="s1",
                role="user",
                content=f"Message {i}",
                created_at=_utcnow(),
            )
            await memory_bank.store_conversation_entry(entry)

        entries = await memory_bank.get_conversation("s1", limit=5)
        assert len(entries) == 5

    @pytest.mark.asyncio
    async def test_store_returns_entry_id(self, memory_bank):
        entry = ConversationEntry(
            entry_id="e1",
            user_id="u1",
            session_id="s1",
            role="user",
            content="Test",
            created_at=_utcnow(),
        )
        result = await memory_bank.store_conversation_entry(entry)
        assert result == "e1"


class TestPredictionTracking:
    @pytest.mark.asyncio
    async def test_store_and_get_pending(self, memory_bank):
        pred = PredictionOutcome(
            outcome_id="o1",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=0.85,
            price_at_prediction=150.0,
            check_window_days=30,
            created_at=_utcnow(),
        )
        result = await memory_bank.store_prediction(pred)
        assert result == "o1"

        pending = await memory_bank.get_pending_predictions()
        assert len(pending) == 1
        assert pending[0].outcome_id == "o1"

    @pytest.mark.asyncio
    async def test_update_prediction_outcome(self, memory_bank):
        pred = PredictionOutcome(
            outcome_id="o1",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=0.85,
            price_at_prediction=150.0,
            created_at=_utcnow(),
        )
        await memory_bank.store_prediction(pred)

        updated = await memory_bank.update_prediction_outcome(
            outcome_id="o1",
            price_at_check=165.0,
            actual_return_pct=0.10,
            outcome="correct",
        )
        assert updated is True

        # No longer pending
        pending = await memory_bank.get_pending_predictions()
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_update_nonexistent_prediction(self, memory_bank):
        result = await memory_bank.update_prediction_outcome(
            outcome_id="nonexistent",
            price_at_check=100.0,
            actual_return_pct=0.0,
            outcome="incorrect",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_prediction_accuracy_empty(self, memory_bank):
        accuracy = await memory_bank.get_prediction_accuracy()
        assert accuracy["total"] == 0
        assert accuracy["correct"] == 0
        assert accuracy["accuracy"] == 0.0

    @pytest.mark.asyncio
    async def test_prediction_accuracy_with_data(self, memory_bank):
        now = _utcnow()
        # 2 correct, 1 incorrect
        for i, (signal, outcome) in enumerate(
            [("BUY", "correct"), ("SELL", "correct"), ("BUY", "incorrect")]
        ):
            pred = PredictionOutcome(
                outcome_id=f"o{i}",
                ticker="AAPL",
                verdict_session_id=f"vs{i}",
                predicted_signal=signal,
                predicted_confidence=0.8,
                price_at_prediction=150.0,
                price_at_check=160.0 if outcome == "correct" else 140.0,
                actual_return_pct=0.07 if outcome == "correct" else -0.07,
                outcome=outcome,
                created_at=now,
                checked_at=now,
            )
            await memory_bank.store_prediction(pred)

        accuracy = await memory_bank.get_prediction_accuracy()
        assert accuracy["total"] == 3
        assert accuracy["correct"] == 2
        assert abs(accuracy["accuracy"] - 2 / 3) < 0.01

    @pytest.mark.asyncio
    async def test_prediction_accuracy_by_ticker(self, memory_bank):
        now = _utcnow()
        for i, (ticker, outcome) in enumerate(
            [("AAPL", "correct"), ("AAPL", "incorrect"), ("MSFT", "correct")]
        ):
            pred = PredictionOutcome(
                outcome_id=f"o{i}",
                ticker=ticker,
                verdict_session_id=f"vs{i}",
                predicted_signal="BUY",
                predicted_confidence=0.8,
                price_at_prediction=150.0,
                outcome=outcome,
                created_at=now,
            )
            await memory_bank.store_prediction(pred)

        aapl_acc = await memory_bank.get_prediction_accuracy(ticker="AAPL")
        assert aapl_acc["total"] == 2
        assert aapl_acc["correct"] == 1

    @pytest.mark.asyncio
    async def test_pending_predictions_excludes_resolved(self, memory_bank):
        now = _utcnow()
        pending = PredictionOutcome(
            outcome_id="o_pending",
            ticker="AAPL",
            verdict_session_id="vs1",
            predicted_signal="BUY",
            predicted_confidence=0.8,
            price_at_prediction=150.0,
            outcome="pending",
            created_at=now,
        )
        resolved = PredictionOutcome(
            outcome_id="o_resolved",
            ticker="MSFT",
            verdict_session_id="vs2",
            predicted_signal="SELL",
            predicted_confidence=0.7,
            price_at_prediction=300.0,
            outcome="correct",
            created_at=now,
        )
        await memory_bank.store_prediction(pending)
        await memory_bank.store_prediction(resolved)

        result = await memory_bank.get_pending_predictions()
        assert len(result) == 1
        assert result[0].outcome_id == "o_pending"


class TestLearnedWeights:
    @pytest.mark.asyncio
    async def test_no_weights_initially(self, memory_bank):
        result = await memory_bank.get_learned_weights()
        assert result is None

    @pytest.mark.asyncio
    async def test_update_and_get(self, memory_bank):
        weights = {
            "valuation_scout": 0.30,
            "momentum_tracker": 0.20,
            "pulse_monitor": 0.15,
            "economy_watcher": 0.20,
            "compliance_checker": 0.15,
        }
        await memory_bank.update_learned_weights(weights)
        result = await memory_bank.get_learned_weights()
        assert result == weights

    @pytest.mark.asyncio
    async def test_update_overwrites(self, memory_bank):
        weights1 = {"valuation_scout": 0.30}
        await memory_bank.update_learned_weights(weights1)

        weights2 = {"valuation_scout": 0.25, "momentum_tracker": 0.25}
        await memory_bank.update_learned_weights(weights2)

        result = await memory_bank.get_learned_weights()
        assert result == weights2


class TestFactoryFunction:
    def test_get_memory_bank_local(self):
        with patch("memory.vertex_memory.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "local"
            mock_settings.return_value.SQLITE_DB_PATH = "data/equityiq.db"
            bank = get_memory_bank()
            assert isinstance(bank, VertexMemoryBank)

    def test_get_memory_bank_production(self):
        with patch("memory.vertex_memory.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.SQLITE_DB_PATH = "data/equityiq.db"
            bank = get_memory_bank()
            # Still VertexMemoryBank in production (Firestore version is future work)
            assert isinstance(bank, VertexMemoryBank)


class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_get_preferences_on_error(self, memory_bank):
        """Preferences should return None on error, not crash."""
        await memory_bank.close()
        # Force a new broken connection
        memory_bank._conn = None
        memory_bank._db_path = "/nonexistent/path/db.sqlite"
        result = await memory_bank.get_preferences("u1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_conversation_on_error(self, memory_bank):
        await memory_bank.close()
        memory_bank._conn = None
        memory_bank._db_path = "/nonexistent/path/db.sqlite"
        result = await memory_bank.get_conversation("s1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pending_predictions_on_error(self, memory_bank):
        await memory_bank.close()
        memory_bank._conn = None
        memory_bank._db_path = "/nonexistent/path/db.sqlite"
        result = await memory_bank.get_pending_predictions()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_learned_weights_on_error(self, memory_bank):
        await memory_bank.close()
        memory_bank._conn = None
        memory_bank._db_path = "/nonexistent/path/db.sqlite"
        result = await memory_bank.get_learned_weights()
        assert result is None

    @pytest.mark.asyncio
    async def test_prediction_accuracy_on_error(self, memory_bank):
        await memory_bank.close()
        memory_bank._conn = None
        memory_bank._db_path = "/nonexistent/path/db.sqlite"
        result = await memory_bank.get_prediction_accuracy()
        assert result["total"] == 0
        assert result["accuracy"] == 0.0
