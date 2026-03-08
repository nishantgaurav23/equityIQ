"""HistoryRetriever -- query layer for past analysis verdicts."""

import logging

from pydantic import BaseModel, field_validator

from config.data_contracts import FinalVerdict
from memory.insight_vault import InsightVault

logger = logging.getLogger(__name__)


class SignalSnapshot(BaseModel):
    """Lightweight model for signal trend entries."""

    session_id: str
    ticker: str
    final_signal: str
    overall_confidence: float
    created_at: str

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class HistoryRetriever:
    """Query layer over InsightVault for historical analysis data."""

    def __init__(self, vault: InsightVault) -> None:
        self._vault = vault

    async def get_ticker_history(
        self,
        ticker: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[FinalVerdict]:
        """Retrieve past verdicts for a ticker, ordered newest first."""
        if not ticker or not ticker.strip():
            return []

        limit = max(1, min(limit, 200))

        try:
            return await self._vault.list_verdicts(ticker=ticker, limit=limit, offset=offset)
        except Exception:
            logger.exception("Failed to get ticker history for %s", ticker)
            return []

    async def get_signal_trend(
        self,
        ticker: str,
        limit: int = 20,
    ) -> list[SignalSnapshot]:
        """Return chronological signal/confidence pairs for a ticker (oldest first)."""
        if not ticker or not ticker.strip():
            return []

        limit = max(1, min(limit, 100))

        try:
            conn = await self._vault._get_connection()
            cursor = await conn.execute(
                "SELECT session_id, ticker, final_signal, overall_confidence, created_at "
                "FROM verdicts WHERE ticker = ? "
                "ORDER BY created_at ASC LIMIT ?",
                (ticker, limit),
            )
            rows = await cursor.fetchall()
            return [
                SignalSnapshot(
                    session_id=row[0],
                    ticker=row[1],
                    final_signal=row[2],
                    overall_confidence=row[3],
                    created_at=row[4],
                )
                for row in rows
            ]
        except Exception:
            logger.exception("Failed to get signal trend for %s", ticker)
            return []

    async def get_recent_verdicts(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> list[FinalVerdict]:
        """Retrieve most recent verdicts across all tickers, newest first."""
        limit = max(1, min(limit, 200))

        try:
            return await self._vault.list_verdicts(limit=limit, offset=offset)
        except Exception:
            logger.exception("Failed to get recent verdicts")
            return []
