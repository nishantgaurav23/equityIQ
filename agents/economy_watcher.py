"""EconomyWatcher -- Macroeconomic analysis agent for EquityIQ.

Uses FRED API for US stocks and World Bank API for Indian stocks.
Classifies the macro regime and returns an EconomyReport with BUY/HOLD/SELL signal.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import EconomyReport
from tools.fred_connector import FredConnector
from tools.india_macro_connector import IndiaMacroConnector
from tools.market_detector import is_indian_ticker

logger = logging.getLogger(__name__)

# Module-level connector instances.
_us_connector = FredConnector()
_india_connector = IndiaMacroConnector()

# Track the current ticker being analyzed (set by analyze() override)
_current_ticker: str = ""


async def get_macro_indicators_tool() -> dict:
    """Fetch macroeconomic indicators for the stock's home market.

    US stocks -> FRED (GDP, CPI, Fed rate, unemployment)
    Indian stocks -> World Bank + RBI (GDP, CPI, repo rate, unemployment)
    """
    try:
        if is_indian_ticker(_current_ticker):
            logger.info("Using India macro data for %s", _current_ticker)
            return await _india_connector.get_macro_indicators()
        return await _us_connector.get_macro_indicators()
    except Exception:
        logger.warning("get_macro_indicators_tool failed")
        return {}


class EconomyWatcher(BaseAnalystAgent):
    """Specialist agent for macroeconomic analysis.

    Automatically routes to FRED (US) or World Bank (India) based on the ticker.
    """

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="economy_watcher",
            output_schema=EconomyReport,
            tools=[get_macro_indicators_tool],
            model=model,
        )

    async def analyze(self, ticker: str) -> EconomyReport:
        """Override to set the current ticker for market detection."""
        global _current_ticker
        _current_ticker = ticker
        return await super().analyze(ticker)


def create_economy_watcher() -> EconomyWatcher:
    """Factory function to create an EconomyWatcher instance."""
    return EconomyWatcher()


economy_watcher = create_economy_watcher()
