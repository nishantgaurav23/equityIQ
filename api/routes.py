"""API routes for EquityIQ -- /analyze, /history, /agents endpoints."""

from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from api.exceptions import (
    AnalysisTimeoutError,
    InvalidTickerError,
    VerdictNotFoundError,
)
from config.data_contracts import FinalVerdict, PortfolioInsight
from memory.history_retriever import SignalSnapshot
from tools.ticker_search import search_tickers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["analysis"])


class PortfolioRequest(BaseModel):
    """Request body for portfolio analysis."""

    tickers: list[str] = Field(..., min_length=1, max_length=10)


@router.post("/analyze/{ticker}", response_model=FinalVerdict)
async def analyze_ticker(ticker: str, request: Request) -> FinalVerdict:
    """Run full multi-agent analysis on a stock ticker.

    Orchestrates all 6 specialist agents in parallel, fuses signals via
    XGBoost/weighted average, applies compliance overrides, and returns
    a 5-level FinalVerdict (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL).
    """
    ticker = ticker.strip().upper()
    if not ticker or len(ticker) > 20:
        raise InvalidTickerError(ticker)

    session_id = str(uuid.uuid4())
    logger.info("Analyze request for %s (session=%s)", ticker, session_id)

    conductor = request.app.state.conductor
    try:
        verdict = await conductor.analyze(ticker, session_id=session_id)
    except asyncio.TimeoutError:
        raise AnalysisTimeoutError(ticker)
    return verdict


@router.post("/portfolio", response_model=PortfolioInsight)
async def analyze_portfolio(body: PortfolioRequest, request: Request) -> PortfolioInsight:
    """Run multi-agent analysis on a portfolio of stock tickers.

    Accepts up to 10 tickers. Each is analyzed in parallel via MarketConductor,
    then aggregated into a PortfolioInsight with diversification score and top pick.
    """
    tickers = [t.strip().upper() for t in body.tickers]
    for t in tickers:
        if not t or len(t) > 20:
            raise InvalidTickerError(t)

    session_id = str(uuid.uuid4())
    logger.info("Portfolio request for %s (session=%s)", tickers, session_id)

    conductor = request.app.state.conductor
    try:
        return await conductor.analyze_portfolio(tickers, session_id=session_id)
    except asyncio.TimeoutError:
        raise AnalysisTimeoutError(",".join(tickers))


@router.get("/history/{ticker}/trend", response_model=list[SignalSnapshot])
async def get_signal_trend(
    ticker: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SignalSnapshot]:
    """Retrieve signal trend for a specific ticker (oldest first)."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise InvalidTickerError(ticker)

    retriever = request.app.state.history_retriever
    return await retriever.get_signal_trend(ticker, limit=limit)


@router.get("/history/{ticker}", response_model=list[FinalVerdict])
async def get_ticker_history(
    ticker: str,
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[FinalVerdict]:
    """Retrieve past analysis verdicts for a specific ticker."""
    ticker = ticker.strip().upper()
    if not ticker:
        raise InvalidTickerError(ticker)

    retriever = request.app.state.history_retriever
    return await retriever.get_ticker_history(ticker, limit=limit, offset=offset)


@router.get("/history", response_model=list[FinalVerdict])
async def get_recent_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[FinalVerdict]:
    """Retrieve most recent analysis verdicts across all tickers."""
    retriever = request.app.state.history_retriever
    return await retriever.get_recent_verdicts(limit=limit, offset=offset)


@router.get("/verdict/{session_id}", response_model=FinalVerdict)
async def get_verdict(session_id: str, request: Request) -> FinalVerdict:
    """Retrieve a specific verdict by session ID."""
    vault = request.app.state.vault
    verdict = await vault.get_verdict(session_id)
    if verdict is None:
        raise VerdictNotFoundError(session_id)
    return verdict


@router.get("/price-history/{ticker}")
async def get_price_history(
    ticker: str,
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Fetch daily OHLCV price history via Yahoo Finance (supports US, India, global)."""
    ticker = ticker.strip()
    if not ticker or len(ticker) > 20:
        raise InvalidTickerError(ticker)

    from tools.yahoo_connector import yahoo

    result = await yahoo.get_price_history(ticker, days=days)

    # If bare ticker returned nothing, try Indian exchange suffixes (.NS, .BO)
    if not result and "." not in ticker:
        for suffix in (".NS", ".BO"):
            result = await yahoo.get_price_history(f"{ticker.upper()}{suffix}", days=days)
            if result:
                break

    if not result:
        # Fallback to Polygon for US tickers
        try:
            from tools.polygon_connector import PolygonConnector

            connector = PolygonConnector()
            try:
                result = await connector.get_price_history(ticker.upper(), days=days)
                if result:
                    result["currency"] = "USD"
            finally:
                await connector.close()
        except Exception:
            pass
    return result or {}


@router.get("/price-history-multi")
async def get_multi_price_history(
    tickers: str = Query(..., description="Comma-separated tickers"),
    days: int = Query(default=90, ge=1, le=365),
) -> dict:
    """Fetch price history for multiple tickers at once."""
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list or len(ticker_list) > 10:
        raise InvalidTickerError(tickers)

    from tools.yahoo_connector import yahoo

    return await yahoo.get_multi_price_history(ticker_list, days=days)


@router.get("/exchange-rate")
async def get_exchange_rate(
    from_currency: str = Query(default="USD"),
    to_currency: str = Query(default="INR"),
) -> dict:
    """Get exchange rate between two currencies."""
    from tools.yahoo_connector import yahoo

    rate = await yahoo.get_exchange_rate(from_currency, to_currency)
    return {
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "rate": rate,
    }


@router.get("/search")
async def search_ticker(
    q: str = "",
    market: str = Query(default="all", description="Filter: us, in, all"),
) -> list[dict]:
    """Search for tickers by company name or symbol (US + India + global)."""
    # Try Yahoo Finance first (global coverage)
    from tools.yahoo_connector import yahoo

    yf_results = await yahoo.search_tickers(q, limit=10)

    if market != "all":
        yf_results = [r for r in yf_results if r.get("locale") == market]

    if yf_results:
        return yf_results[:8]

    # Fallback to Polygon (US only)
    return await search_tickers(q, limit=8)


@router.get("/agents")
async def list_agents(request: Request) -> list[dict]:
    """List all available specialist agents and their status."""
    conductor = request.app.state.conductor
    agents = conductor._lazy_load_agents()
    return [
        {
            "name": agent.name,
            "status": "available",
            "card": agent.get_agent_card(),
        }
        for agent in agents
    ]
