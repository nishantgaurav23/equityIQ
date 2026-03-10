"""ValuationScout -- Fundamentals analysis agent for EquityIQ.

Uses Polygon.io for US stocks and yfinance for Indian stocks (NSE/BSE).
Evaluates valuation metrics and returns a ValuationReport with BUY/HOLD/SELL signal.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import ValuationReport
from tools.market_detector import is_indian_ticker
from tools.polygon_connector import PolygonConnector
from tools.yahoo_connector import YahooConnector

logger = logging.getLogger(__name__)

# Module-level connector instances (shared across tool calls).
_polygon = PolygonConnector()
_yahoo = YahooConnector()


async def get_fundamentals_tool(ticker: str) -> dict:
    """Fetch fundamental financial ratios for a ticker.

    Routes to yfinance for Indian tickers (.NS/.BO), Polygon.io for US.
    """
    try:
        if is_indian_ticker(ticker):
            return await _yahoo.get_fundamentals(ticker)
        return await _polygon.get_fundamentals(ticker)
    except Exception:
        logger.warning("get_fundamentals_tool failed for %s", ticker)
        return {}


async def get_price_history_tool(ticker: str) -> dict:
    """Fetch 1-year daily price history for a ticker.

    Routes to yfinance for Indian tickers (.NS/.BO), Polygon.io for US.
    """
    try:
        if is_indian_ticker(ticker):
            return await _yahoo.get_price_history(ticker, days=365)
        return await _polygon.get_price_history(ticker, days=365)
    except Exception:
        logger.warning("get_price_history_tool failed for %s", ticker)
        return {}


class ValuationScout(BaseAnalystAgent):
    """Specialist agent for fundamental stock valuation analysis."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="valuation_scout",
            output_schema=ValuationReport,
            tools=[get_fundamentals_tool, get_price_history_tool],
            model=model,
        )


def create_valuation_scout() -> ValuationScout:
    """Factory function to create a ValuationScout instance."""
    return ValuationScout()


valuation_scout = create_valuation_scout()
