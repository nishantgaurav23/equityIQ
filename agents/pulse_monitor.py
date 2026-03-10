"""PulseMonitor -- News sentiment analysis agent for EquityIQ.

Uses NewsConnector for sentiment scoring and PolygonConnector for additional
company news. For Indian stocks, searches using the company name (sans suffix)
to get relevant results. Returns a PulseReport with BUY/HOLD/SELL signal. Port 8003.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import PulseReport
from tools.market_detector import get_company_name_for_search, is_indian_ticker
from tools.news_connector import NewsConnector
from tools.polygon_connector import PolygonConnector

logger = logging.getLogger(__name__)

# Module-level connector instances (shared across tool calls).
_news_connector = NewsConnector()
_polygon_connector = PolygonConnector()


async def get_news_sentiment_tool(ticker: str) -> dict:
    """Fetch news sentiment analysis for a ticker from NewsAPI.

    For Indian tickers, searches by company name (e.g., 'RELIANCE' instead of
    'RELIANCE.NS') for better news coverage.
    """
    try:
        search_query = ticker
        if is_indian_ticker(ticker):
            # Search by company name for better Indian news coverage
            search_query = get_company_name_for_search(ticker)
            # Also try to get the full company name via yfinance
            try:
                import yfinance as yf
                info = yf.Ticker(ticker).info or {}
                short_name = info.get("shortName", "")
                if short_name:
                    search_query = short_name
            except Exception:
                pass
            logger.info("Searching Indian news for %s (query: %s)", ticker, search_query)
        return await _news_connector.get_news_sentiment(search_query)
    except Exception:
        logger.warning("get_news_sentiment_tool failed for %s", ticker)
        return {}


async def get_company_news_tool(ticker: str) -> dict:
    """Fetch company news headlines from Polygon.io (US stocks only).

    For Indian stocks, Polygon has no coverage so this returns empty gracefully.
    """
    try:
        if is_indian_ticker(ticker):
            # Polygon doesn't cover Indian stocks
            return {}
        return await _polygon_connector.get_company_news(ticker)
    except Exception:
        logger.warning("get_company_news_tool failed for %s", ticker)
        return {}


class PulseMonitorAgent(BaseAnalystAgent):
    """News sentiment analyst using NewsAPI and Polygon company news."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="pulse_monitor",
            output_schema=PulseReport,
            tools=[get_news_sentiment_tool, get_company_news_tool],
            model=model,
        )


def create_pulse_monitor() -> PulseMonitorAgent:
    """Factory function to create a PulseMonitorAgent instance."""
    return PulseMonitorAgent()


pulse_monitor = create_pulse_monitor()
