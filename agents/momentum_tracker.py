"""Momentum Tracker agent -- technical analysis using price momentum indicators.

Uses polygon_connector for price history and technical_engine for RSI, MACD,
SMA crossovers, and volatility. Returns a MomentumReport. Port 8002.
"""

from __future__ import annotations

import logging

from agents.base_agent import BaseAnalystAgent
from config.data_contracts import MomentumReport
from tools.polygon_connector import PolygonConnector
from tools.technical_engine import calc_macd, calc_rsi, calc_sma

logger = logging.getLogger(__name__)


def _empty_result() -> dict:
    """Return a fallback dict with all None values."""
    return {
        "rsi_14": None,
        "macd_signal": None,
        "above_sma_50": None,
        "above_sma_200": None,
        "volume_trend": None,
        "price_momentum_score": None,
    }


def _classify_volume_trend(volumes: list[float]) -> str:
    """Classify volume trend as increasing, decreasing, or stable."""
    if len(volumes) < 30:
        return "stable"
    recent_avg = sum(volumes[-10:]) / 10
    longer_avg = sum(volumes[-30:]) / 30
    if longer_avg == 0:
        return "stable"
    ratio = recent_avg / longer_avg
    if ratio > 1.2:
        return "increasing"
    if ratio < 0.8:
        return "decreasing"
    return "stable"


def _compute_momentum_score(
    rsi_14: float,
    histogram: float,
    above_sma_50: bool,
    above_sma_200: bool,
) -> float:
    """Compute composite price momentum score in [-1.0, 1.0]."""
    # RSI component: maps 0-100 -> -1 to 1
    rsi_component = (rsi_14 - 50.0) / 50.0

    # MACD component
    if histogram > 0:
        macd_component = 1.0
    elif histogram < 0:
        macd_component = -1.0
    else:
        macd_component = 0.0

    # SMA component
    sma_component = 0.0
    sma_component += 0.5 if above_sma_50 else -0.5
    sma_component += 0.5 if above_sma_200 else -0.5

    score = (rsi_component + macd_component + sma_component) / 3.0
    return max(-1.0, min(1.0, score))


async def get_technical_analysis(ticker: str) -> dict:
    """Fetch price history and compute all technical indicators.

    Returns a dict with rsi_14, macd_signal, above_sma_50, above_sma_200,
    volume_trend, and price_momentum_score. On error, all values are None.
    """
    try:
        connector = PolygonConnector()
        price_data = await connector.get_price_history(ticker, days=250)

        if not price_data or "prices" not in price_data:
            return _empty_result()

        prices = price_data["prices"]
        volumes = price_data.get("volumes", [])

        if not prices:
            return _empty_result()

        # Compute indicators
        rsi_14 = calc_rsi(prices, period=14)
        macd = calc_macd(prices)
        macd_signal = macd.get("signal_line", 0.0)
        histogram = macd.get("histogram", 0.0)

        sma_50 = calc_sma(prices, period=50)
        sma_200 = calc_sma(prices, period=200)

        current_price = prices[-1]
        above_sma_50 = current_price > sma_50
        above_sma_200 = current_price > sma_200

        volume_trend = _classify_volume_trend(volumes)

        price_momentum_score = _compute_momentum_score(
            rsi_14, histogram, above_sma_50, above_sma_200
        )

        return {
            "rsi_14": rsi_14,
            "macd_signal": macd_signal,
            "above_sma_50": above_sma_50,
            "above_sma_200": above_sma_200,
            "volume_trend": volume_trend,
            "price_momentum_score": price_momentum_score,
        }
    except Exception as exc:
        logger.warning("get_technical_analysis failed for %s: %s", ticker, exc)
        return _empty_result()


class MomentumTrackerAgent(BaseAnalystAgent):
    """Technical analysis agent using price momentum indicators."""

    def __init__(self, model: str = "gemini-3-flash-preview") -> None:
        super().__init__(
            agent_name="momentum_tracker",
            output_schema=MomentumReport,
            tools=[get_technical_analysis],
            model=model,
        )


def create_momentum_tracker() -> MomentumTrackerAgent:
    """Factory function to create a MomentumTrackerAgent instance."""
    return MomentumTrackerAgent()


momentum_tracker = create_momentum_tracker()
