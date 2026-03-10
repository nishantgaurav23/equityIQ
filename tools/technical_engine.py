"""Pure Python technical indicator calculator.

Provides calc_rsi(), calc_macd(), calc_sma(), and calc_volatility() using
numpy only. No external API calls. Consumed by MomentumTracker agent.
"""

from __future__ import annotations

import math

import numpy as np


def _calc_ema(values: list[float], period: int) -> list[float]:
    """Compute Exponential Moving Average series.

    Uses SMA as the seed for the first EMA value, then applies the
    standard EMA formula: EMA_t = price * k + EMA_{t-1} * (1 - k)
    where k = 2 / (period + 1).
    """
    if not values or period <= 0:
        return []
    if len(values) < period:
        return []

    k = 2.0 / (period + 1)
    ema_series: list[float] = []

    # Seed with SMA of the first `period` values
    sma_seed = sum(values[:period]) / period
    ema_series.append(sma_seed)

    for price in values[period:]:
        ema_series.append(price * k + ema_series[-1] * (1 - k))

    return ema_series


def calc_rsi(prices: list[float], period: int = 14) -> float:
    """Calculate Relative Strength Index using Wilder's smoothing.

    Args:
        prices: Closing prices, oldest first.
        period: Lookback period (default 14).

    Returns:
        RSI value clamped to [0.0, 100.0]. Returns 50.0 for insufficient data.
    """
    if len(prices) < period + 1:
        return 50.0

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Wilder's smoothing: first average is SMA, then EMA with alpha = 1/period
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0
    if avg_gain == 0.0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return max(0.0, min(100.0, rsi))


def calc_macd(
    prices: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, float]:
    """Calculate MACD line, signal line, and histogram.

    Args:
        prices: Closing prices, oldest first.
        fast: Fast EMA period (default 12).
        slow: Slow EMA period (default 26).
        signal: Signal EMA period (default 9).

    Returns:
        Dict with macd_line, signal_line, histogram. Zeros if insufficient data.
    """
    zeros = {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0}

    if len(prices) < slow + signal:
        return zeros

    ema_fast = _calc_ema(prices, fast)
    ema_slow = _calc_ema(prices, slow)

    if not ema_fast or not ema_slow:
        return zeros

    # Align: ema_fast is longer, trim from front to match ema_slow length
    offset = len(ema_fast) - len(ema_slow)
    macd_line_series = [ema_fast[offset + i] - ema_slow[i] for i in range(len(ema_slow))]

    if len(macd_line_series) < signal:
        return zeros

    signal_series = _calc_ema(macd_line_series, signal)
    if not signal_series:
        return zeros

    macd_val = macd_line_series[-1]
    signal_val = signal_series[-1]
    histogram = macd_val - signal_val

    return {
        "macd_line": float(macd_val),
        "signal_line": float(signal_val),
        "histogram": float(histogram),
    }


def calc_sma(prices: list[float], period: int) -> float:
    """Calculate Simple Moving Average over the last `period` prices.

    Args:
        prices: Closing prices, oldest first.
        period: Number of prices to average.

    Returns:
        SMA value. Returns 0.0 for empty list; averages all available if < period.
    """
    if not prices:
        return 0.0
    window = prices[-period:] if len(prices) >= period else prices
    return float(sum(window) / len(window))


def calc_volatility(prices: list[float], period: int = 252) -> float:
    """Calculate annualized volatility from daily closing prices.

    Args:
        prices: Closing prices, oldest first.
        period: Trading days for annualization (default 252).

    Returns:
        Annualized volatility as a decimal (e.g. 0.25 = 25%). Returns 0.0
        for fewer than 2 prices or constant prices.
    """
    if len(prices) < 2:
        return 0.0

    arr = np.array(prices, dtype=float)
    log_returns = np.log(arr[1:] / arr[:-1])

    std = float(np.std(log_returns, ddof=1))
    if math.isnan(std) or std == 0.0:
        return 0.0

    return std * math.sqrt(period)
