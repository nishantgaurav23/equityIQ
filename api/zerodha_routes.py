"""Zerodha broker integration API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel

from integrations.zerodha import ZerodhaClient, ZerodhaHolding, ZerodhaPortfolio, ZerodhaPosition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/zerodha", tags=["zerodha"])


class LoginResponse(BaseModel):
    login_url: str


class CallbackResponse(BaseModel):
    access_token: str
    user_id: str


class AnalyzeResponse(BaseModel):
    tickers: list[str]
    message: str


def _get_client(request: Request) -> ZerodhaClient:
    """Get or create ZerodhaClient from app state."""
    if not hasattr(request.app.state, "zerodha_client"):
        request.app.state.zerodha_client = ZerodhaClient()
    return request.app.state.zerodha_client


@router.get("/login", response_model=LoginResponse)
async def zerodha_login(request: Request) -> LoginResponse:
    """Return Zerodha Kite Connect login URL."""
    client = _get_client(request)
    return LoginResponse(login_url=client.get_login_url())


@router.get("/callback", response_model=CallbackResponse)
async def zerodha_callback(
    request_token: str,
    request: Request,
) -> CallbackResponse:
    """OAuth2 callback -- exchange request_token for access_token."""
    client = _get_client(request)
    try:
        data = await client.exchange_request_token(request_token)
        return CallbackResponse(
            access_token=data["access_token"],
            user_id=data.get("user_id", ""),
        )
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail=str(e))


@router.get("/holdings", response_model=list[ZerodhaHolding])
async def zerodha_holdings(
    request: Request,
    x_zerodha_token: str = Header(..., alias="X-Zerodha-Token"),
) -> list[ZerodhaHolding]:
    """Fetch holdings from connected Zerodha account."""
    client = _get_client(request)
    try:
        return await client.get_holdings(x_zerodha_token)
    except PermissionError:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid or expired Zerodha token")


@router.get("/positions", response_model=list[ZerodhaPosition])
async def zerodha_positions(
    request: Request,
    x_zerodha_token: str = Header(..., alias="X-Zerodha-Token"),
) -> list[ZerodhaPosition]:
    """Fetch positions from connected Zerodha account."""
    client = _get_client(request)
    try:
        return await client.get_positions(x_zerodha_token)
    except PermissionError:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid or expired Zerodha token")


@router.get("/portfolio", response_model=ZerodhaPortfolio)
async def zerodha_portfolio(
    request: Request,
    x_zerodha_token: str = Header(..., alias="X-Zerodha-Token"),
) -> ZerodhaPortfolio:
    """Full portfolio summary from connected Zerodha account."""
    client = _get_client(request)
    try:
        return await client.get_portfolio_summary(x_zerodha_token)
    except PermissionError:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid or expired Zerodha token")


@router.post("/analyze", response_model=AnalyzeResponse)
async def zerodha_analyze(
    request: Request,
    x_zerodha_token: str = Header(..., alias="X-Zerodha-Token"),
) -> AnalyzeResponse:
    """Analyze Zerodha holdings via EquityIQ multi-agent pipeline."""
    client = _get_client(request)
    try:
        portfolio = await client.get_portfolio_summary(x_zerodha_token)
    except PermissionError:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid or expired Zerodha token")

    tickers = portfolio.equityiq_tickers
    if not tickers:
        return AnalyzeResponse(tickers=[], message="No equity holdings found to analyze")

    # Limit to 10 tickers max (EquityIQ portfolio limit)
    tickers = tickers[:10]

    conductor = request.app.state.conductor
    try:
        await conductor.analyze_portfolio(tickers)
    except Exception:
        logger.exception("Portfolio analysis failed for Zerodha holdings")
        return AnalyzeResponse(
            tickers=tickers,
            message=f"Analysis initiated for {len(tickers)} tickers but encountered errors",
        )

    return AnalyzeResponse(
        tickers=tickers,
        message=f"Analysis complete for {len(tickers)} Zerodha holdings",
    )
