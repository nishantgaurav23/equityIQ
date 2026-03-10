"""RiskGuardian -- Portfolio risk management agent for EquityIQ.

Uses Polygon.io (US) or yfinance (India) for price history and real benchmark
data (SPY / Nifty50) for beta calculation. India path adds VIX, circuit breaker,
and F&O ban checks. Position size is always capped at 0.10 (10%).
"""

from __future__ import annotations

import logging

import httpx
import numpy as np

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import RiskGuardianReport
from models.risk_calculator import (
    calc_annualized_volatility,
    calc_beta,
    calc_max_drawdown,
    calc_position_size,
    calc_sharpe,
    calc_var_95,
)
from tools.market_detector import get_market, is_indian_ticker
from tools.polygon_connector import PolygonConnector
from tools.yahoo_connector import YahooConnector

logger = logging.getLogger(__name__)

# Default risk-free rates (annualized, as decimal fractions).
_US_RISK_FREE_RATE = 0.05  # ~Fed funds rate
_INDIA_RISK_FREE_RATE = 0.065  # ~RBI repo rate

# Module-level connector instances (shared across tool calls).
_polygon = PolygonConnector()
_yahoo = YahooConnector()

# NSE headers for ban list endpoint (same pattern as india_compliance_connector).
_NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}


async def get_price_history_tool(ticker: str) -> dict:
    """Fetch 1-year daily price history. Routes to Polygon (US) or Yahoo (India)."""
    try:
        if is_indian_ticker(ticker):
            return await _yahoo.get_price_history(ticker, days=365)
        return await _polygon.get_price_history(ticker, days=365)
    except Exception:
        logger.warning("get_price_history_tool failed for %s", ticker)
        return {}


async def _get_benchmark_returns(market: str) -> tuple[np.ndarray, str]:
    """Fetch real benchmark price history and compute daily returns.

    US -> SPY via Polygon, India -> ^NSEI (Nifty 50) via Yahoo.
    Returns (returns_array, benchmark_name). Empty array on failure.
    """
    if market == "in":
        benchmark_ticker = "^NSEI"
        data = await _yahoo.get_price_history(benchmark_ticker, days=365)
    else:
        benchmark_ticker = "SPY"
        data = await _polygon.get_price_history(benchmark_ticker, days=365)

    prices = data.get("prices", [])
    if not prices or len(prices) < 2:
        return np.array([]), benchmark_ticker

    prices_arr = np.asarray(prices, dtype=float)
    returns = np.diff(prices_arr) / prices_arr[:-1]
    return returns, benchmark_ticker


async def _get_risk_free_rate(market: str) -> float:
    """Return the appropriate risk-free rate for the market.

    India: tries to fetch RBI repo rate from IndiaMacroConnector, falls back to 6.5%.
    US: returns 5% (Fed funds rate approximation).
    """
    if market == "in":
        try:
            from tools.india_macro_connector import IndiaMacroConnector

            connector = IndiaMacroConnector()
            rate = await connector._fetch_rbi_repo_rate()
            # rate comes as percentage (e.g. 6.5), convert to decimal fraction
            return rate / 100.0
        except Exception:
            return _INDIA_RISK_FREE_RATE
    return _US_RISK_FREE_RATE


async def calc_risk_metrics_tool(ticker: str) -> dict:
    """Compute portfolio risk metrics using real benchmark data.

    Fetches stock prices and benchmark (SPY for US, Nifty50 for India),
    computes beta against the real benchmark, and uses the correct
    risk-free rate for Sharpe ratio calculation.
    """
    try:
        market = get_market(ticker)

        # Fetch stock prices (routed by market)
        data = await get_price_history_tool(ticker)
        prices = data.get("prices", [])

        if not prices or len(prices) < 2:
            return {}

        prices_arr = np.asarray(prices, dtype=float)
        returns = np.diff(prices_arr) / prices_arr[:-1]

        # Fetch REAL benchmark returns (SPY or ^NSEI)
        benchmark_returns, benchmark_name = await _get_benchmark_returns(market)

        # Beta: use real benchmark if available, align lengths
        if len(benchmark_returns) > 0:
            min_len = min(len(returns), len(benchmark_returns))
            beta = calc_beta(returns[-min_len:], benchmark_returns[-min_len:])
        else:
            beta = 1.0  # default when benchmark unavailable

        # Risk-free rate for correct market
        risk_free_rate = await _get_risk_free_rate(market)

        volatility = calc_annualized_volatility(returns)
        sharpe = calc_sharpe(returns, risk_free_rate=risk_free_rate)
        max_dd = calc_max_drawdown(prices)
        var_95 = calc_var_95(returns)
        position = calc_position_size(volatility)

        return {
            "beta": round(beta, 4),
            "annualized_volatility": round(volatility, 4),
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_dd, 4),
            "var_95": round(var_95, 6),
            "suggested_position_size": round(position, 4),
            "benchmark_used": benchmark_name,
            "risk_free_rate_used": risk_free_rate,
        }
    except Exception:
        logger.warning("calc_risk_metrics_tool failed for %s", ticker)
        return {}


async def get_india_market_risk_tool(ticker: str) -> dict:
    """Fetch India-specific market risk data: India VIX, circuit breaker, F&O ban.

    Returns {} for non-Indian tickers or on total failure.
    """
    if not is_indian_ticker(ticker):
        return {}

    try:
        result: dict = {}

        # India VIX via yfinance (^INDIAVIX)
        try:
            vix_data = await _yahoo.get_price_history("^INDIAVIX", days=7)
            vix_prices = vix_data.get("prices", [])
            if vix_prices:
                result["india_vix"] = round(vix_prices[-1], 2)
        except Exception:
            pass

        # Circuit breaker bands (SEBI rules for F&O stocks)
        result["circuit_breaker_band"] = "10%/15%/20%"

        # F&O ban status from NSE daily ban list
        try:
            symbol = ticker.replace(".NS", "").replace(".BO", "").upper()
            async with httpx.AsyncClient(
                timeout=10.0, headers=_NSE_HEADERS, follow_redirects=True
            ) as client:
                # NSE requires session cookie -- hit main page first
                await client.get("https://www.nseindia.com", timeout=5.0)
                resp = await client.get("https://www.nseindia.com/api/live-analysis-ban")
                if resp.status_code == 200:
                    ban_data = resp.json()
                    banned_symbols = [item.get("symbol", "") for item in ban_data.get("data", [])]
                    result["fno_ban"] = symbol in banned_symbols
        except Exception:
            result["fno_ban"] = None

        return result
    except Exception:
        logger.warning("get_india_market_risk_tool failed for %s", ticker)
        return {}


class RiskGuardian(BaseAnalystAgent):
    """Specialist agent for portfolio risk assessment and position sizing."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="risk_guardian",
            output_schema=RiskGuardianReport,
            tools=[
                get_price_history_tool,
                calc_risk_metrics_tool,
                get_india_market_risk_tool,
            ],
            model=model,
        )


def create_risk_guardian() -> RiskGuardian:
    """Factory function to create a RiskGuardian instance."""
    return RiskGuardian()


risk_guardian = create_risk_guardian()
