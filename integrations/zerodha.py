"""Zerodha Kite Connect integration -- OAuth2, holdings, positions, symbol mapping."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone

import httpx
from cachetools import TTLCache
from pydantic import BaseModel, Field, field_validator

from config.settings import get_settings

logger = logging.getLogger(__name__)

KITE_API_BASE = "https://api.kite.trade"
KITE_LOGIN_URL = "https://kite.zerodha.com/connect/login"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class ZerodhaHolding(BaseModel):
    """A single delivery holding from Zerodha."""

    tradingsymbol: str
    exchange: str  # NSE or BSE
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    day_change_percentage: float = 0.0
    equityiq_ticker: str = ""

    @field_validator("day_change_percentage", mode="before")
    @classmethod
    def default_day_change(cls, v):
        return float(v) if v is not None else 0.0


class ZerodhaPosition(BaseModel):
    """A single position (day or net) from Zerodha."""

    tradingsymbol: str
    exchange: str
    product: str  # CNC, MIS, NRML
    quantity: int
    buy_price: float
    sell_price: float
    pnl: float
    equityiq_ticker: str = ""


class ZerodhaPortfolio(BaseModel):
    """Aggregated portfolio summary from Zerodha."""

    holdings: list[ZerodhaHolding]
    positions: list[ZerodhaPosition]
    total_invested: float
    current_value: float
    total_pnl: float
    total_pnl_percentage: float
    day_pnl: float
    equityiq_tickers: list[str] = Field(default_factory=list)
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Symbol Mapping
# ---------------------------------------------------------------------------

def map_zerodha_to_equityiq(tradingsymbol: str, exchange: str) -> str:
    """Map Zerodha symbol + exchange to EquityIQ ticker.

    NSE -> .NS suffix, BSE -> .BO suffix.
    Returns empty string for non-equity instruments (futures, options).
    """
    exchange = exchange.upper().strip()
    symbol = tradingsymbol.strip()

    # Skip non-equity segments (index derivatives, futures, options)
    # Derivative symbols have digits before CE/PE (e.g., NIFTY23JUN18000CE)
    non_equity_prefixes = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY")
    if any(symbol.startswith(p) for p in non_equity_prefixes) or symbol.endswith("FUT"):
        return ""
    # Options have a strike price (digits) followed by CE/PE
    if re.search(r"\d+(CE|PE)$", symbol):
        return ""

    suffix_map = {"NSE": ".NS", "BSE": ".BO"}
    suffix = suffix_map.get(exchange, "")
    if not suffix:
        return ""
    return f"{symbol}{suffix}"


def map_equityiq_to_zerodha(ticker: str) -> tuple[str, str]:
    """Reverse map EquityIQ ticker to (tradingsymbol, exchange).

    E.g. RELIANCE.NS -> ("RELIANCE", "NSE")
    Returns ("", "") if format is unrecognized.
    """
    ticker = ticker.strip()
    if ticker.endswith(".NS"):
        return (ticker[:-3], "NSE")
    if ticker.endswith(".BO"):
        return (ticker[:-3], "BSE")
    return ("", "")


# ---------------------------------------------------------------------------
# Zerodha Client
# ---------------------------------------------------------------------------

class ZerodhaClient:
    """Async client for Kite Connect API."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.ZERODHA_API_KEY
        self.api_secret = settings.ZERODHA_API_SECRET
        self.redirect_url = settings.ZERODHA_REDIRECT_URL
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(3)  # 3 req/s rate limit
        self._holdings_cache: TTLCache = TTLCache(maxsize=10, ttl=30)
        self._positions_cache: TTLCache = TTLCache(maxsize=10, ttl=30)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # -- OAuth2 --

    def get_login_url(self) -> str:
        """Return the Kite Connect login URL for user to authenticate."""
        return f"{KITE_LOGIN_URL}?v=3&api_key={self.api_key}"

    async def exchange_request_token(self, request_token: str) -> dict:
        """Exchange request token for access token via Kite Connect API.

        Returns dict with access_token, user_id, etc.
        Raises ValueError on failure.
        """
        checksum = hashlib.sha256(
            f"{self.api_key}{request_token}{self.api_secret}".encode()
        ).hexdigest()

        payload = {
            "api_key": self.api_key,
            "request_token": request_token,
            "checksum": checksum,
        }

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.post(
                    f"{KITE_API_BASE}/session/token", data=payload
                )

            if resp.status_code == 403:
                raise ValueError("Invalid or expired request token")
            resp.raise_for_status()

            data = resp.json().get("data", {})
            if not data.get("access_token"):
                raise ValueError("No access_token in response")
            return data

        except httpx.HTTPStatusError as e:
            logger.error("Token exchange failed: %s", e)
            raise ValueError(f"Token exchange failed: {e.response.status_code}") from e
        except httpx.HTTPError as e:
            logger.error("Network error during token exchange: %s", e)
            raise ValueError(f"Network error: {e}") from e

    def _auth_headers(self, access_token: str) -> dict:
        return {"Authorization": f"token {self.api_key}:{access_token}"}

    # -- Holdings --

    async def get_holdings(self, access_token: str) -> list[ZerodhaHolding]:
        """Fetch delivery holdings from Kite Connect."""
        cache_key = f"holdings:{access_token[:8]}"
        cached = self._holdings_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.get(
                    f"{KITE_API_BASE}/portfolio/holdings",
                    headers=self._auth_headers(access_token),
                )

            if resp.status_code == 403:
                raise PermissionError("Invalid or expired access token")
            resp.raise_for_status()

            raw_holdings = resp.json().get("data", [])
            holdings = []
            for h in raw_holdings:
                ticker = map_zerodha_to_equityiq(
                    h.get("tradingsymbol", ""), h.get("exchange", "")
                )
                holdings.append(
                    ZerodhaHolding(
                        tradingsymbol=h.get("tradingsymbol", ""),
                        exchange=h.get("exchange", ""),
                        quantity=h.get("quantity", 0),
                        average_price=h.get("average_price", 0.0),
                        last_price=h.get("last_price", 0.0),
                        pnl=h.get("pnl", 0.0),
                        day_change_percentage=h.get("day_change_percentage", 0.0),
                        equityiq_ticker=ticker,
                    )
                )
            self._holdings_cache[cache_key] = holdings
            return holdings

        except (PermissionError, ValueError):
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch holdings: %s", e)
            return []

    # -- Positions --

    async def get_positions(self, access_token: str) -> list[ZerodhaPosition]:
        """Fetch day + net positions from Kite Connect."""
        cache_key = f"positions:{access_token[:8]}"
        cached = self._positions_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.get(
                    f"{KITE_API_BASE}/portfolio/positions",
                    headers=self._auth_headers(access_token),
                )

            if resp.status_code == 403:
                raise PermissionError("Invalid or expired access token")
            resp.raise_for_status()

            data = resp.json().get("data", {})
            positions = []
            for pos_type in ("net", "day"):
                for p in data.get(pos_type, []):
                    ticker = map_zerodha_to_equityiq(
                        p.get("tradingsymbol", ""), p.get("exchange", "")
                    )
                    positions.append(
                        ZerodhaPosition(
                            tradingsymbol=p.get("tradingsymbol", ""),
                            exchange=p.get("exchange", ""),
                            product=p.get("product", ""),
                            quantity=p.get("quantity", 0),
                            buy_price=p.get("buy_price", 0.0) or p.get("average_price", 0.0),
                            sell_price=p.get("sell_price", 0.0),
                            pnl=p.get("pnl", 0.0) or p.get("unrealised", 0.0),
                            equityiq_ticker=ticker,
                        )
                    )
            self._positions_cache[cache_key] = positions
            return positions

        except (PermissionError, ValueError):
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch positions: %s", e)
            return []

    # -- Portfolio Summary --

    async def get_portfolio_summary(self, access_token: str) -> ZerodhaPortfolio:
        """Aggregate holdings and positions into a portfolio summary."""
        holdings, positions = await asyncio.gather(
            self.get_holdings(access_token),
            self.get_positions(access_token),
        )

        total_invested = sum(h.average_price * h.quantity for h in holdings)
        current_value = sum(h.last_price * h.quantity for h in holdings)
        total_pnl = sum(h.pnl for h in holdings)
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
        day_pnl = sum(
            h.last_price * h.quantity * h.day_change_percentage / 100
            for h in holdings
        )

        # Collect unique EquityIQ tickers (non-empty only)
        tickers = sorted(
            {h.equityiq_ticker for h in holdings if h.equityiq_ticker}
            | {p.equityiq_ticker for p in positions if p.equityiq_ticker}
        )

        return ZerodhaPortfolio(
            holdings=holdings,
            positions=positions,
            total_invested=round(total_invested, 2),
            current_value=round(current_value, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_percentage=round(total_pnl_pct, 2),
            day_pnl=round(day_pnl, 2),
            equityiq_tickers=tickers,
        )
