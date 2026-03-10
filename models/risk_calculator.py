"""Portfolio risk calculator -- S4.2.

Pure-math functions for beta, Sharpe ratio, VaR, max drawdown,
position sizing, and annualized volatility. No external API calls.
"""

from __future__ import annotations

import math

import numpy as np


def calc_beta(
    stock_returns: list[float] | np.ndarray,
    market_returns: list[float] | np.ndarray,
) -> float:
    """Calculate beta coefficient (covariance / variance of market).

    Returns 1.0 (market-neutral default) for edge cases:
    empty arrays, single element, or zero market variance.
    Raises ValueError if array lengths differ.
    """
    stock = np.asarray(stock_returns, dtype=float)
    market = np.asarray(market_returns, dtype=float)

    if stock.shape != market.shape:
        raise ValueError(
            f"stock_returns length ({len(stock)}) != market_returns length ({len(market)})"
        )

    if len(stock) <= 1:
        return 1.0

    market_var = np.var(market, ddof=1)
    if market_var == 0.0:
        return 1.0

    covariance = np.cov(stock, market, ddof=1)[0, 1]
    return float(covariance / market_var)


def calc_sharpe(
    returns: list[float] | np.ndarray,
    risk_free_rate: float = 0.05,
) -> float:
    """Calculate annualized Sharpe ratio.

    Formula: (mean_daily - daily_rf) / std_daily * sqrt(252)
    Returns 0.0 for empty/single-element arrays or zero std.
    """
    arr = np.asarray(returns, dtype=float)

    if len(arr) <= 1:
        return 0.0

    std = np.std(arr, ddof=1)
    if std == 0.0:
        return 0.0

    daily_rf = risk_free_rate / 252
    mean_daily = np.mean(arr)
    return float((mean_daily - daily_rf) / std * math.sqrt(252))


def calc_var_95(returns: list[float] | np.ndarray) -> float:
    """Calculate historical Value-at-Risk at 95% confidence (5th percentile).

    Returns 0.0 for empty arrays.
    """
    arr = np.asarray(returns, dtype=float)

    if len(arr) == 0:
        return 0.0

    return float(np.percentile(arr, 5))


def calc_max_drawdown(prices: list[float] | np.ndarray) -> float:
    """Calculate maximum peak-to-trough drawdown from a price series.

    Returns a negative fraction (e.g., -0.25 = 25% drawdown).
    Returns 0.0 for empty/single-element arrays or monotonically increasing prices.
    """
    arr = np.asarray(prices, dtype=float)

    if len(arr) <= 1:
        return 0.0

    peak = arr[0]
    max_dd = 0.0

    for price in arr[1:]:
        if price > peak:
            peak = price
        dd = (price - peak) / peak
        if dd < max_dd:
            max_dd = dd

    return float(max_dd)


def calc_position_size(
    volatility: float,
    max_portfolio_risk: float = 0.02,
    max_position: float = 0.10,
) -> float:
    """Calculate suggested position size via volatility targeting.

    Formula: min(max_portfolio_risk / volatility, max_position)
    Returns max_position for zero/negative volatility.
    Hard cap: position size never exceeds max_position (default 0.10).
    """
    if volatility <= 0:
        return max_position

    size = max_portfolio_risk / volatility
    return min(max(size, 0.0), max_position)


def calc_annualized_volatility(returns: list[float] | np.ndarray) -> float:
    """Calculate annualized volatility: std(daily_returns) * sqrt(252).

    Returns 0.0 for empty/single-element arrays or zero variance.
    """
    arr = np.asarray(returns, dtype=float)

    if len(arr) <= 1:
        return 0.0

    std = np.std(arr, ddof=1)
    if std == 0.0:
        return 0.0

    return float(std * math.sqrt(252))
