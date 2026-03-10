"""Alpaca Trading API integration -- positions, account, paper orders, symbol mapping."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from cachetools import TTLCache
from pydantic import BaseModel, Field

from config.settings import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class AlpacaPosition(BaseModel):
    """A single open position from Alpaca."""

    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pl: float
    unrealized_plpc: float  # Percentage as decimal
    side: str  # "long" or "short"
    equityiq_ticker: str = ""


class AlpacaAccount(BaseModel):
    """Alpaca account summary."""

    account_id: str
    buying_power: float
    portfolio_value: float
    cash: float
    equity: float
    last_equity: float
    day_trade_count: int
    pattern_day_trader: bool
    trading_blocked: bool
    account_blocked: bool


class AlpacaOrder(BaseModel):
    """An order placed via Alpaca."""

    order_id: str
    symbol: str
    qty: float
    side: str  # "buy" or "sell"
    order_type: str  # "market", "limit"
    status: str  # "new", "filled", "partially_filled", "cancelled"
    filled_qty: float = 0.0
    filled_avg_price: float = 0.0
    submitted_at: datetime


class AlpacaPortfolio(BaseModel):
    """Aggregated portfolio summary from Alpaca."""

    positions: list[AlpacaPosition]
    account: AlpacaAccount
    portfolio_value: float
    buying_power: float
    total_unrealized_pl: float
    total_unrealized_plpc: float
    day_pl: float
    equityiq_tickers: list[str] = Field(default_factory=list)
    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Symbol Mapping
# ---------------------------------------------------------------------------


def map_alpaca_to_equityiq(symbol: str) -> str:
    """Map Alpaca symbol to EquityIQ ticker.

    US stocks pass through as-is. Class B shares with dots are converted
    to dashes (BRK.B -> BRK-B).
    """
    symbol = symbol.strip()
    if not symbol:
        return ""
    # Convert class B share notation: BRK.B -> BRK-B
    if "." in symbol:
        symbol = symbol.replace(".", "-")
    return symbol


def map_equityiq_to_alpaca(ticker: str) -> str:
    """Reverse map EquityIQ ticker to Alpaca symbol.

    Returns empty string for Indian tickers (.NS/.BO).
    Converts BRK-B -> BRK.B for class B shares.
    """
    ticker = ticker.strip()
    if not ticker:
        return ""
    # Reject Indian tickers
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return ""
    # Convert class B share notation back: BRK-B -> BRK.B
    if "-" in ticker:
        ticker = ticker.replace("-", ".")
    return ticker


# ---------------------------------------------------------------------------
# Alpaca Client
# ---------------------------------------------------------------------------


class AlpacaClient:
    """Async client for Alpaca Trading API."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.ALPACA_API_KEY
        self.api_secret = settings.ALPACA_API_SECRET
        self.base_url = settings.ALPACA_BASE_URL.rstrip("/")
        self.data_url = settings.ALPACA_DATA_URL.rstrip("/")
        self.allow_paper_trading = settings.ALPACA_ALLOW_PAPER_TRADING
        self._client: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(10)  # 200 req/min ~= 3.3 req/s
        self._positions_cache: TTLCache = TTLCache(maxsize=10, ttl=15)
        self._account_cache: TTLCache = TTLCache(maxsize=10, ttl=15)

    @property
    def is_paper_trading(self) -> bool:
        """Check if client is configured for paper trading."""
        return "paper-api" in self.base_url

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    # -- Account --

    async def get_account(self) -> AlpacaAccount:
        """Fetch account info from Alpaca."""
        cache_key = f"account:{self.api_key[:8]}"
        cached = self._account_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.get(
                    f"{self.base_url}/v2/account",
                    headers=self._auth_headers(),
                )

            if resp.status_code in (401, 403):
                raise PermissionError("Invalid or expired Alpaca credentials")
            resp.raise_for_status()

            data = resp.json()
            account = AlpacaAccount(
                account_id=data.get("id", ""),
                buying_power=float(data.get("buying_power", 0)),
                portfolio_value=float(data.get("portfolio_value", 0)),
                cash=float(data.get("cash", 0)),
                equity=float(data.get("equity", 0)),
                last_equity=float(data.get("last_equity", 0)),
                day_trade_count=int(data.get("daytrade_count", 0)),
                pattern_day_trader=data.get("pattern_day_trader", False),
                trading_blocked=data.get("trading_blocked", False),
                account_blocked=data.get("account_blocked", False),
            )
            self._account_cache[cache_key] = account
            return account

        except PermissionError:
            raise
        except httpx.HTTPError as e:
            logger.error("Network error fetching Alpaca account: %s", e)
            raise ConnectionError(f"Network error: {e}") from e

    # -- Positions --

    async def get_positions(self) -> list[AlpacaPosition]:
        """Fetch open positions from Alpaca."""
        cache_key = f"positions:{self.api_key[:8]}"
        cached = self._positions_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.get(
                    f"{self.base_url}/v2/positions",
                    headers=self._auth_headers(),
                )

            if resp.status_code in (401, 403):
                raise PermissionError("Invalid or expired Alpaca credentials")
            resp.raise_for_status()

            raw_positions = resp.json()
            positions = []
            for p in raw_positions:
                ticker = map_alpaca_to_equityiq(p.get("symbol", ""))
                positions.append(
                    AlpacaPosition(
                        symbol=p.get("symbol", ""),
                        qty=float(p.get("qty", 0)),
                        avg_entry_price=float(p.get("avg_entry_price", 0)),
                        current_price=float(p.get("current_price", 0)),
                        market_value=float(p.get("market_value", 0)),
                        unrealized_pl=float(p.get("unrealized_pl", 0)),
                        unrealized_plpc=float(p.get("unrealized_plpc", 0)),
                        side=p.get("side", "long"),
                        equityiq_ticker=ticker,
                    )
                )
            self._positions_cache[cache_key] = positions
            return positions

        except (PermissionError, ValueError):
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to fetch Alpaca positions: %s", e)
            return []

    # -- Portfolio Summary --

    async def get_portfolio_summary(self) -> AlpacaPortfolio:
        """Aggregate positions + account into a portfolio summary."""
        account, positions = await asyncio.gather(
            self.get_account(),
            self.get_positions(),
        )

        total_unrealized_pl = sum(p.unrealized_pl for p in positions)
        total_market_value = sum(p.market_value for p in positions)
        total_unrealized_plpc = (
            (total_unrealized_pl / (total_market_value - total_unrealized_pl) * 100)
            if (total_market_value - total_unrealized_pl) > 0
            else 0.0
        )
        day_pl = account.equity - account.last_equity

        tickers = sorted({p.equityiq_ticker for p in positions if p.equityiq_ticker})

        return AlpacaPortfolio(
            positions=positions,
            account=account,
            portfolio_value=account.portfolio_value,
            buying_power=account.buying_power,
            total_unrealized_pl=round(total_unrealized_pl, 2),
            total_unrealized_plpc=round(total_unrealized_plpc, 2),
            day_pl=round(day_pl, 2),
            equityiq_tickers=tickers,
        )

    # -- Paper Orders --

    async def place_paper_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
    ) -> AlpacaOrder:
        """Place a paper order via Alpaca. Only works on paper trading account."""
        if not self.allow_paper_trading:
            raise PermissionError("Paper trading is not enabled")
        if not self.is_paper_trading:
            raise PermissionError("Live trading is not allowed")

        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": "day",
        }

        try:
            async with self._semaphore:
                client = await self._get_client()
                resp = await client.post(
                    f"{self.base_url}/v2/orders",
                    headers=self._auth_headers(),
                    json=payload,
                )

            if resp.status_code in (401, 403):
                raise PermissionError("Invalid or expired Alpaca credentials")
            resp.raise_for_status()

            data = resp.json()
            return AlpacaOrder(
                order_id=data.get("id", ""),
                symbol=data.get("symbol", ""),
                qty=float(data.get("qty", 0)),
                side=data.get("side", ""),
                order_type=data.get("type", ""),
                status=data.get("status", ""),
                filled_qty=float(data.get("filled_qty", 0) or 0),
                filled_avg_price=float(data.get("filled_avg_price", 0) or 0),
                submitted_at=data.get("submitted_at", datetime.now(timezone.utc).isoformat()),
            )

        except PermissionError:
            raise
        except httpx.HTTPError as e:
            logger.error("Failed to place Alpaca order: %s", e)
            raise ConnectionError(f"Network error: {e}") from e
