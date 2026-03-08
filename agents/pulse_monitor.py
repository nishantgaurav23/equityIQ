"""PulseMonitor -- News sentiment analysis agent for EquityIQ.

Uses NewsConnector for sentiment scoring and PolygonConnector for additional
company news. Returns a PulseReport with BUY/HOLD/SELL signal. Port 8003.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import PulseReport
from tools.news_connector import NewsConnector
from tools.polygon_connector import PolygonConnector

logger = logging.getLogger(__name__)

# Module-level connector instances (shared across tool calls).
_news_connector = NewsConnector()
_polygon_connector = PolygonConnector()


async def get_news_sentiment_tool(ticker: str) -> dict:
    """Fetch news sentiment analysis for a ticker from NewsAPI."""
    try:
        return await _news_connector.get_news_sentiment(ticker)
    except Exception:
        logger.warning("get_news_sentiment_tool failed for %s", ticker)
        return {}


async def get_company_news_tool(ticker: str) -> dict:
    """Fetch company news headlines for a ticker from Polygon.io."""
    try:
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
