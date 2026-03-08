"""ValuationScout -- Fundamentals analysis agent for EquityIQ.

Uses Polygon.io to fetch financial data, evaluates valuation metrics,
and returns a ValuationReport with BUY/HOLD/SELL signal.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import ValuationReport
from tools.polygon_connector import PolygonConnector

logger = logging.getLogger(__name__)

# Module-level connector instance (shared across tool calls).
_connector = PolygonConnector()


async def get_fundamentals_tool(ticker: str) -> dict:
    """Fetch fundamental financial ratios for a ticker from Polygon.io."""
    try:
        return await _connector.get_fundamentals(ticker)
    except Exception:
        logger.warning("get_fundamentals_tool failed for %s", ticker)
        return {}


async def get_price_history_tool(ticker: str) -> dict:
    """Fetch 1-year daily price history for a ticker from Polygon.io."""
    try:
        return await _connector.get_price_history(ticker, days=365)
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
