"""ComplianceChecker -- Regulatory risk analysis agent for EquityIQ.

Uses SecConnector for US companies (SEC Edgar) and IndiaComplianceConnector
for Indian companies (NSE/BSE filings). Returns a ComplianceReport with
BUY/HOLD/SELL signal. going_concern/restatement flags trigger SELL override. Port 8005.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import ComplianceReport
from tools.india_compliance_connector import IndiaComplianceConnector
from tools.market_detector import is_indian_ticker
from tools.sec_connector import SecConnector

logger = logging.getLogger(__name__)

# Module-level connector instances.
_sec_connector = SecConnector()
_india_connector = IndiaComplianceConnector()


async def get_sec_filings_tool(ticker: str) -> dict | list:
    """Fetch regulatory filings for a ticker.

    US stocks -> SEC Edgar filings
    Indian stocks -> NSE/BSE corporate announcements + yfinance governance data
    """
    try:
        if is_indian_ticker(ticker):
            logger.info("Using India compliance data for %s", ticker)
            return await _india_connector.get_filings(ticker)
        return await _sec_connector.get_sec_filings(ticker)
    except Exception:
        logger.warning("get_sec_filings_tool failed for %s", ticker)
        return {}


async def score_risk_tool(ticker: str) -> dict:
    """Analyze filings for regulatory risk scoring.

    US stocks -> SEC risk scoring
    Indian stocks -> NSE/BSE/SEBI risk scoring
    """
    try:
        if is_indian_ticker(ticker):
            return await _india_connector.score_risk(ticker)
        return await _sec_connector.score_risk(ticker)
    except Exception:
        logger.warning("score_risk_tool failed for %s", ticker)
        return {}


class ComplianceCheckerAgent(BaseAnalystAgent):
    """Regulatory risk analyst using SEC Edgar (US) and NSE/BSE (India)."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="compliance_checker",
            output_schema=ComplianceReport,
            tools=[get_sec_filings_tool, score_risk_tool],
            model=model,
        )


def create_compliance_checker() -> ComplianceCheckerAgent:
    """Factory function to create a ComplianceCheckerAgent instance."""
    return ComplianceCheckerAgent()


compliance_checker = create_compliance_checker()
