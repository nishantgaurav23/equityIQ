"""API endpoints for webhook alerts -- watchlist CRUD, history, scheduler control."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AddWatchRequest(BaseModel):
    """Request body for adding a ticker to watchlist."""

    ticker: str
    webhook_url: str
    channel: str = "webhook"


@router.post("/watchlist")
async def add_watchlist_entry(body: AddWatchRequest, request: Request):
    """Add a ticker to the alert watchlist."""
    engine = request.app.state.alert_engine
    entry = await engine.add_watch(body.ticker, body.webhook_url, body.channel)
    return entry.model_dump()


@router.get("/watchlist")
async def get_watchlist(request: Request):
    """List all active watchlist entries."""
    engine = request.app.state.alert_engine
    entries = await engine.get_watchlist()
    return [e.model_dump() for e in entries]


@router.delete("/watchlist/{entry_id}")
async def remove_watchlist_entry(entry_id: int, request: Request):
    """Remove a ticker from the watchlist."""
    engine = request.app.state.alert_engine
    removed = await engine.remove_watch(entry_id)
    return {"removed": removed, "entry_id": entry_id}


@router.get("/history")
async def get_alert_history(request: Request, limit: int = Query(default=50, le=200)):
    """Get recent alert history."""
    engine = request.app.state.alert_engine
    alerts = await engine.get_recent_alerts(limit=limit)
    return [a.model_dump() for a in alerts]


@router.get("/history/{ticker}")
async def get_alerts_for_ticker(ticker: str, request: Request):
    """Get alert history for a specific ticker."""
    engine = request.app.state.alert_engine
    alerts = await engine.get_alerts_by_ticker(ticker)
    return [a.model_dump() for a in alerts]


@router.post("/check-now")
async def check_now(request: Request):
    """Trigger immediate signal check on all watched tickers."""
    engine = request.app.state.alert_engine
    conductor = request.app.state.conductor
    vault = request.app.state.vault
    try:
        changes = await engine.check_signals(conductor, vault)
        return {"changes": [c.model_dump() for c in changes]}
    except Exception as exc:
        logger.error("check-now failed: %s", exc)
        return {"changes": [], "error": str(exc)}


@router.get("/status")
async def scheduler_status(request: Request):
    """Get scheduler status."""
    engine = request.app.state.alert_engine
    return engine.get_status()
