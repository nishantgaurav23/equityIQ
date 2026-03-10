"""Alpaca broker integration API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from integrations.alpaca import (
    AlpacaAccount,
    AlpacaClient,
    AlpacaOrder,
    AlpacaPortfolio,
    AlpacaPosition,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alpaca", tags=["alpaca"])


class AnalyzeResponse(BaseModel):
    tickers: list[str]
    message: str


class PaperOrderRequest(BaseModel):
    symbol: str
    qty: int
    side: str  # "buy" or "sell"
    order_type: str = "market"


def _get_client(request: Request) -> AlpacaClient:
    """Get or create AlpacaClient from app state."""
    if not hasattr(request.app.state, "alpaca_client"):
        request.app.state.alpaca_client = AlpacaClient()
    return request.app.state.alpaca_client


@router.get("/account", response_model=AlpacaAccount)
async def alpaca_account(
    request: Request,
    x_alpaca_key: str = Header(..., alias="X-Alpaca-Key"),
    x_alpaca_secret: str = Header(..., alias="X-Alpaca-Secret"),
) -> AlpacaAccount:
    """Fetch Alpaca account info."""
    client = _get_client(request)
    try:
        return await client.get_account()
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid Alpaca credentials")
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/positions", response_model=list[AlpacaPosition])
async def alpaca_positions(
    request: Request,
    x_alpaca_key: str = Header(..., alias="X-Alpaca-Key"),
    x_alpaca_secret: str = Header(..., alias="X-Alpaca-Secret"),
) -> list[AlpacaPosition]:
    """Fetch open positions from connected Alpaca account."""
    client = _get_client(request)
    try:
        return await client.get_positions()
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid Alpaca credentials")


@router.get("/portfolio", response_model=AlpacaPortfolio)
async def alpaca_portfolio(
    request: Request,
    x_alpaca_key: str = Header(..., alias="X-Alpaca-Key"),
    x_alpaca_secret: str = Header(..., alias="X-Alpaca-Secret"),
) -> AlpacaPortfolio:
    """Full portfolio summary from connected Alpaca account."""
    client = _get_client(request)
    try:
        return await client.get_portfolio_summary()
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid Alpaca credentials")
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/analyze", response_model=AnalyzeResponse)
async def alpaca_analyze(
    request: Request,
    x_alpaca_key: str = Header(..., alias="X-Alpaca-Key"),
    x_alpaca_secret: str = Header(..., alias="X-Alpaca-Secret"),
) -> AnalyzeResponse:
    """Analyze Alpaca holdings via EquityIQ multi-agent pipeline."""
    client = _get_client(request)
    try:
        portfolio = await client.get_portfolio_summary()
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid Alpaca credentials")
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))

    tickers = portfolio.equityiq_tickers
    if not tickers:
        return AnalyzeResponse(tickers=[], message="No positions found to analyze")

    # Limit to 10 tickers max (EquityIQ portfolio limit)
    tickers = tickers[:10]

    conductor = request.app.state.conductor
    try:
        await conductor.analyze_portfolio(tickers)
    except Exception:
        logger.exception("Portfolio analysis failed for Alpaca holdings")
        return AnalyzeResponse(
            tickers=tickers,
            message=f"Analysis initiated for {len(tickers)} tickers but encountered errors",
        )

    return AnalyzeResponse(
        tickers=tickers,
        message=f"Analysis complete for {len(tickers)} Alpaca positions",
    )


@router.post("/paper-order", response_model=AlpacaOrder)
async def alpaca_paper_order(
    order: PaperOrderRequest,
    request: Request,
    x_alpaca_key: str = Header(..., alias="X-Alpaca-Key"),
    x_alpaca_secret: str = Header(..., alias="X-Alpaca-Secret"),
) -> AlpacaOrder:
    """Place a paper order via Alpaca (gated behind ALPACA_ALLOW_PAPER_TRADING)."""
    client = _get_client(request)
    try:
        return await client.place_paper_order(
            symbol=order.symbol,
            qty=order.qty,
            side=order.side,
            order_type=order.order_type,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e))
