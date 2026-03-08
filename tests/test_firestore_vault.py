"""Tests for FirestoreVault -- Firestore-backed storage backend."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.data_contracts import FinalVerdict


def _make_verdict(ticker="AAPL", signal="BUY", confidence=0.8, session_id=None):
    """Create a FinalVerdict for testing."""
    return FinalVerdict(
        ticker=ticker,
        final_signal=signal,
        overall_confidence=confidence,
        price_target=150.0,
        analyst_signals={"valuation": "BUY"},
        risk_summary="Low risk",
        key_drivers=["Strong fundamentals"],
        session_id=session_id or "",
    )


@pytest.fixture
def mock_settings():
    """Mock settings with production config."""
    settings = MagicMock()
    settings.ENVIRONMENT = "production"
    settings.GCP_PROJECT_ID = "test-project-id"
    settings.SQLITE_DB_PATH = "data/equityiq.db"
    return settings


def _make_mock_client():
    """Create a mock Firestore AsyncClient with sync chain methods."""
    client = MagicMock()
    # collection() and document() are sync, returning refs
    collection_ref = MagicMock()
    client.collection.return_value = collection_ref
    doc_ref = MagicMock()
    collection_ref.document.return_value = doc_ref
    # I/O operations are async
    doc_ref.set = AsyncMock()
    doc_ref.get = AsyncMock()
    doc_ref.delete = AsyncMock()
    # close is async
    client.close = AsyncMock()
    return client


# --- FR-2: initialize() ---


async def test_initialize_creates_client(mock_settings):
    """FirestoreVault.initialize() creates Firestore client with correct project_id."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_cls.return_value = _make_mock_client()
        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()

        mock_cls.assert_called_once_with(project="test-project-id")


async def test_initialize_missing_project_id(mock_settings):
    """Raises ValueError when GCP_PROJECT_ID is empty."""
    mock_settings.GCP_PROJECT_ID = ""
    with patch("memory.firestore_vault.get_settings", return_value=mock_settings):
        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
            await vault.initialize()


# --- FR-3: store_verdict() ---


async def test_store_verdict_returns_session_id(mock_settings):
    """store_verdict() stores doc and returns session_id."""
    sid = str(uuid.uuid4())
    verdict = _make_verdict(session_id=sid)

    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.store_verdict(verdict)

        assert result == sid
        mock_client.collection.assert_called_with("verdicts")
        mock_client.collection.return_value.document.return_value.set.assert_called_once()


async def test_store_verdict_generates_session_id(mock_settings):
    """Generates uuid4 when verdict.session_id is empty."""
    verdict = _make_verdict(session_id="")

    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.store_verdict(verdict)

        assert result != ""
        uuid.UUID(result)


# --- FR-4: get_verdict() ---


async def test_get_verdict_found(mock_settings):
    """get_verdict() returns FinalVerdict for existing session_id."""
    sid = str(uuid.uuid4())
    verdict = _make_verdict(session_id=sid)

    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        mock_doc_snapshot.to_dict.return_value = {"verdict_json": verdict.model_dump_json()}
        mock_client.collection.return_value.document.return_value.get.return_value = (
            mock_doc_snapshot
        )

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.get_verdict(sid)

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.session_id == sid


async def test_get_verdict_not_found(mock_settings):
    """get_verdict() returns None for missing session_id."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        mock_client.collection.return_value.document.return_value.get.return_value = (
            mock_doc_snapshot
        )

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.get_verdict("nonexistent")

        assert result is None


async def test_get_verdict_firestore_error(mock_settings):
    """get_verdict() returns None on Firestore error."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client
        mock_client.collection.return_value.document.return_value.get = AsyncMock(
            side_effect=Exception("Firestore error")
        )

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.get_verdict("some-id")

        assert result is None


# --- FR-5: list_verdicts() ---


async def test_list_verdicts_all(mock_settings):
    """list_verdicts() returns all verdicts ordered by created_at DESC."""
    verdict1 = _make_verdict(ticker="AAPL", session_id="s1")
    verdict2 = _make_verdict(ticker="GOOGL", session_id="s2")

    doc1 = MagicMock()
    doc1.to_dict.return_value = {"verdict_json": verdict1.model_dump_json()}
    doc2 = MagicMock()
    doc2.to_dict.return_value = {"verdict_json": verdict2.model_dump_json()}

    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_query = MagicMock()
        mock_collection = mock_client.collection.return_value
        mock_collection.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get = AsyncMock(return_value=[doc1, doc2])

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        results = await vault.list_verdicts()

        assert len(results) == 2
        mock_collection.order_by.assert_called_once()


async def test_list_verdicts_by_ticker(mock_settings):
    """list_verdicts(ticker='AAPL') filters correctly."""
    verdict = _make_verdict(ticker="AAPL", session_id="s1")
    doc = MagicMock()
    doc.to_dict.return_value = {"verdict_json": verdict.model_dump_json()}

    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_query = MagicMock()
        mock_collection = mock_client.collection.return_value
        mock_collection.where.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get = AsyncMock(return_value=[doc])

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        results = await vault.list_verdicts(ticker="AAPL")

        assert len(results) == 1
        assert results[0].ticker == "AAPL"
        mock_collection.where.assert_called_once()


async def test_list_verdicts_limit_cap(mock_settings):
    """limit capped at 200."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_query = MagicMock()
        mock_collection = mock_client.collection.return_value
        mock_collection.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.get = AsyncMock(return_value=[])

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        await vault.list_verdicts(limit=500)

        mock_query.limit.assert_called_with(200)


async def test_list_verdicts_firestore_error(mock_settings):
    """Returns empty list on error."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        mock_client.collection.return_value.order_by.side_effect = Exception("Firestore error")

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        results = await vault.list_verdicts()

        assert results == []


# --- FR-6: delete_verdict() ---


async def test_delete_verdict_found(mock_settings):
    """delete_verdict() returns True when doc exists."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        doc_ref = mock_client.collection.return_value.document.return_value
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = True
        doc_ref.get = AsyncMock(return_value=mock_doc_snapshot)

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.delete_verdict("some-id")

        assert result is True
        doc_ref.delete.assert_called_once()


async def test_delete_verdict_not_found(mock_settings):
    """delete_verdict() returns False when doc missing."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        doc_ref = mock_client.collection.return_value.document.return_value
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.exists = False
        doc_ref.get = AsyncMock(return_value=mock_doc_snapshot)

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        result = await vault.delete_verdict("nonexistent")

        assert result is False


# --- FR-7: close() ---


async def test_close_cleans_up(mock_settings):
    """close() closes client, subsequent calls safe."""
    with (
        patch("memory.firestore_vault.get_settings", return_value=mock_settings),
        patch("memory.firestore_vault.firestore.AsyncClient") as mock_cls,
    ):
        mock_client = _make_mock_client()
        mock_cls.return_value = mock_client

        from memory.firestore_vault import FirestoreVault

        vault = FirestoreVault()
        await vault.initialize()
        await vault.close()

        mock_client.close.assert_called_once()

        # Second close is safe (no-op)
        await vault.close()


# --- FR-8: get_vault() factory ---


async def test_get_vault_production(mock_settings):
    """get_vault() returns FirestoreVault when ENVIRONMENT=production."""
    mock_settings.ENVIRONMENT = "production"
    with patch("memory.firestore_vault.get_settings", return_value=mock_settings):
        from memory.firestore_vault import FirestoreVault, get_vault

        vault = get_vault()
        assert isinstance(vault, FirestoreVault)


async def test_get_vault_local(mock_settings):
    """get_vault() returns InsightVault when ENVIRONMENT=local."""
    mock_settings.ENVIRONMENT = "local"
    with patch("memory.firestore_vault.get_settings", return_value=mock_settings):
        from memory.firestore_vault import get_vault
        from memory.insight_vault import InsightVault

        vault = get_vault()
        assert isinstance(vault, InsightVault)
