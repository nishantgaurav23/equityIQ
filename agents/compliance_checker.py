"""ComplianceChecker -- Regulatory risk analysis agent for EquityIQ.

Uses SecConnector for SEC filing data and risk scoring. Returns a ComplianceReport
with BUY/HOLD/SELL signal. going_concern/restatement flags trigger SELL override. Port 8005.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import ComplianceReport
from tools.sec_connector import SecConnector

logger = logging.getLogger(__name__)

# Module-level connector instance (shared across tool calls).
_sec_connector = SecConnector()


async def get_sec_filings_tool(ticker: str) -> dict | list:
    """Fetch recent SEC filings for a ticker from SEC Edgar."""
    try:
        return await _sec_connector.get_sec_filings(ticker)
    except Exception:
        logger.warning("get_sec_filings_tool failed for %s", ticker)
        return {}


async def score_risk_tool(ticker: str) -> dict:
    """Analyze SEC filings for regulatory risk scoring."""
    try:
        return await _sec_connector.score_risk(ticker)
    except Exception:
        logger.warning("score_risk_tool failed for %s", ticker)
        return {}


class ComplianceCheckerAgent(BaseAnalystAgent):
    """Regulatory risk analyst using SEC Edgar filings and risk scoring."""

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
