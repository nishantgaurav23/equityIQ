"""EconomyWatcher -- Macroeconomic analysis agent for EquityIQ.

Uses FRED API to fetch macro indicators, classifies the macro regime,
and returns an EconomyReport with BUY/HOLD/SELL signal.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import EconomyReport
from tools.fred_connector import FredConnector

logger = logging.getLogger(__name__)

# Module-level connector instance (shared across tool calls).
_connector = FredConnector()


async def get_macro_indicators_tool() -> dict:
    """Fetch macroeconomic indicators (GDP, inflation, Fed rate, unemployment) from FRED."""
    try:
        return await _connector.get_macro_indicators()
    except Exception:
        logger.warning("get_macro_indicators_tool failed")
        return {}


class EconomyWatcher(BaseAnalystAgent):
    """Specialist agent for macroeconomic analysis."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="economy_watcher",
            output_schema=EconomyReport,
            tools=[get_macro_indicators_tool],
            model=model,
        )


def create_economy_watcher() -> EconomyWatcher:
    """Factory function to create an EconomyWatcher instance."""
    return EconomyWatcher()


economy_watcher = create_economy_watcher()
