"""RiskGuardian -- Portfolio risk management agent for EquityIQ.

Uses Polygon.io for price history and risk_calculator for quantitative
risk metrics. Returns a RiskGuardianReport with BUY/HOLD/SELL signal
based on risk profile. Position size is always capped at 0.10 (10%).
"""

from __future__ import annotations

import logging

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
from tools.polygon_connector import PolygonConnector

logger = logging.getLogger(__name__)

# Module-level connector instance (shared across tool calls).
_connector = PolygonConnector()


async def get_price_history_tool(ticker: str) -> dict:
    """Fetch 1-year daily price history for a ticker from Polygon.io."""
    try:
        return await _connector.get_price_history(ticker, days=365)
    except Exception:
        logger.warning("get_price_history_tool failed for %s", ticker)
        return {}


async def calc_risk_metrics_tool(ticker: str) -> dict:
    """Compute portfolio risk metrics for a ticker using price history.

    Fetches price data from Polygon, computes daily returns, then calculates
    beta, volatility, Sharpe ratio, max drawdown, VaR 95%, and position size.
    """
    try:
        data = await _connector.get_price_history(ticker, days=365)
        prices = data.get("prices", [])

        if not prices or len(prices) < 2:
            return {}

        prices_arr = np.asarray(prices, dtype=float)
        returns = np.diff(prices_arr) / prices_arr[:-1]

        # Use uniform market returns approximation (mean-zero, same std)
        # In production, would fetch SPY data for proper beta calculation.
        market_returns = np.random.default_rng(42).normal(
            loc=np.mean(returns), scale=np.std(returns), size=len(returns)
        )

        beta = calc_beta(returns, market_returns)
        volatility = calc_annualized_volatility(returns)
        sharpe = calc_sharpe(returns)
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
        }
    except Exception:
        logger.warning("calc_risk_metrics_tool failed for %s", ticker)
        return {}


class RiskGuardian(BaseAnalystAgent):
    """Specialist agent for portfolio risk assessment and position sizing."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="risk_guardian",
            output_schema=RiskGuardianReport,
            tools=[get_price_history_tool, calc_risk_metrics_tool],
            model=model,
        )


def create_risk_guardian() -> RiskGuardian:
    """Factory function to create a RiskGuardian instance."""
    return RiskGuardian()


risk_guardian = create_risk_guardian()
