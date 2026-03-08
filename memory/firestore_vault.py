"""FirestoreVault -- async Firestore storage for FinalVerdict objects (production backend)."""

import logging
import uuid
from datetime import datetime, timezone

from google.cloud import firestore

from config.data_contracts import FinalVerdict
from config.settings import get_settings
from memory.insight_vault import InsightVault

logger = logging.getLogger(__name__)

_COLLECTION = "verdicts"


class FirestoreVault:
    """Async Firestore-backed storage for analysis verdicts.

    Same interface as InsightVault but uses Google Cloud Firestore.
    Selected when ENVIRONMENT == 'production'.
    """

    def __init__(self):
        self._client: firestore.AsyncClient | None = None
        self._settings = get_settings()

    async def initialize(self) -> None:
        """Create Firestore async client. Requires GCP_PROJECT_ID."""
        project_id = self._settings.GCP_PROJECT_ID
        if not project_id:
            raise ValueError(
                "GCP_PROJECT_ID is required for FirestoreVault. "
                "Set it in .env or environment variables."
            )
        try:
            self._client = firestore.AsyncClient(project=project_id)
        except Exception:
            logger.exception("Failed to initialize FirestoreVault for project %s", project_id)
            raise

    async def store_verdict(self, verdict: FinalVerdict) -> str:
        """Store a FinalVerdict as a Firestore document. Returns session_id."""
        session_id = verdict.session_id or str(uuid.uuid4())
        verdict.session_id = session_id
        created_at = datetime.now(timezone.utc).isoformat()

        doc_data = {
            "session_id": session_id,
            "ticker": verdict.ticker,
            "verdict_json": verdict.model_dump_json(),
            "final_signal": verdict.final_signal,
            "overall_confidence": verdict.overall_confidence,
            "created_at": created_at,
        }

        try:
            doc_ref = self._client.collection(_COLLECTION).document(session_id)
            await doc_ref.set(doc_data)
        except Exception:
            logger.exception("Failed to store verdict for session %s", session_id)
            raise

        return session_id

    async def get_verdict(self, session_id: str) -> FinalVerdict | None:
        """Retrieve a single verdict by session_id. Returns None if not found."""
        try:
            doc_ref = self._client.collection(_COLLECTION).document(session_id)
            doc = await doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            return FinalVerdict.model_validate_json(data["verdict_json"])
        except Exception:
            logger.exception("Failed to get verdict for session %s", session_id)
            return None

    async def list_verdicts(
        self,
        ticker: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FinalVerdict]:
        """List verdicts, optionally filtered by ticker. Ordered by created_at DESC."""
        limit = min(limit, 200)

        try:
            collection_ref = self._client.collection(_COLLECTION)

            if ticker:
                query = collection_ref.where(filter=firestore.FieldFilter("ticker", "==", ticker))
                query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            else:
                query = collection_ref.order_by("created_at", direction=firestore.Query.DESCENDING)

            query = query.offset(offset).limit(limit)
            docs = await query.get()

            return [FinalVerdict.model_validate_json(doc.to_dict()["verdict_json"]) for doc in docs]
        except Exception:
            logger.exception("Failed to list verdicts")
            return []

    async def delete_verdict(self, session_id: str) -> bool:
        """Delete a verdict by session_id. Returns True if deleted, False if not found."""
        try:
            doc_ref = self._client.collection(_COLLECTION).document(session_id)
            doc = await doc_ref.get()
            if not doc.exists:
                return False
            await doc_ref.delete()
            return True
        except Exception:
            logger.exception("Failed to delete verdict for session %s", session_id)
            return False

    async def close(self) -> None:
        """Close the Firestore client connection."""
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:
                logger.exception("Error closing FirestoreVault connection")
            finally:
                self._client = None


def get_vault() -> InsightVault | FirestoreVault:
    """Factory: returns FirestoreVault for production, InsightVault otherwise."""
    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        return FirestoreVault()
    return InsightVault()
