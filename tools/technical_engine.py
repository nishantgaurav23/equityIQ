"""
What It Does:
    Pure Python math engine - no API calls. Takes raw price/volume list from polygon_connector.py and compute RSI, MACD, SMA,
    and a composite momentum score. This is the only tool file with no HTTP client.

Why It's Needed:
    Polygon gives you raw prices. MomentumTracker needs RSI, MACD, SMA - these are calculated, not fetched. Keeping
    math separate from API calls makes both easier to test.

How It Helps:
    - agents/momentum_tracker.py calls compute_all(prices, volumes)
    - agents/risk_guardian.py calls compute_volatility(prices) and compute_max_drawdown(prices)
"""
import math
from typing import Optional

class TechnicalEngine:
    """
    Pure Python technical indicator calculator.
    No API calls - takes raw price lists and returns computed indicators.
    """
    def __init__(self):
        pass # no state needed - all methods are stateless.

    def compute_rsi(self, prices: list[float], period: int = 14) -> float | None:
        """
        Computes RSI (Relative Strength Index) over given period.
        Returns float 0–100. Below 30 = oversold, above 70 = overbought.
        Returns None if not enough price data.

        Args:
            prices: list[float] <- closing prices oldest to newest
            period: int <- default 14

        Returns:
            float | None <- RSI value 0-100, None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        try:
            gains = []
            losses = []

            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0.0)
                elif change < 0:
                    gains.append(0.0)
                    losses.append(abs(change))
                else:
                    gains.append(0.0)
                    losses.append(0.0)
            
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period

            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return round(rsi, 2)
        
        except Exception:
            return None
        
    def _compute_ema(self, prices: list[float], period: int) -> Optional[float]:
        """
        Private helper - computes Exponential Moving Average.
        Called by compute_macd. Not used directly by agents.
        Returns float EMA value or None
        """
        if len(prices) < period:
            return None

        try:
            multiplier = 2 / (period + 1)
            ema        = prices[0]

            for price in prices[1:]:
                ema = (price - ema) * multiplier + ema

            return round(ema, 4)

        except Exception:
            return None

    def compute_macd(self, prices: list[float]) -> Optional[dict]:
        """
        Computes MACD line, signal line, histogram, and crossover direction.
        Returns dict or None if insufficient data (need at least 26 prices).
        """
        if len(prices) < 26:
            return None

        try:
            ema_12 = self._compute_ema(prices, 12)
            ema_26 = self._compute_ema(prices, 26)

            if ema_12 is None or ema_26 is None:
                return None

            macd_line   = ema_12 - ema_26
            signal_line = macd_line * 0.9
            histogram   = macd_line - signal_line

            if macd_line > signal_line:
                crossover = "bullish_cross"
            elif macd_line < signal_line:
                crossover = "bearish_cross"
            else:
                crossover = "neutral"

            return {
                "macd_line":   round(macd_line, 4),
                "signal_line": round(signal_line, 4),
                "histogram":   round(histogram, 4),
                "crossover":   crossover,
            }

        except Exception:
            return None

    def compute_sma(self, prices: list[float], period: int) -> Optional[float]:
        """
        Computes Simple Moving Average over last `period` prices.
        Returns float or None if not enough prices.
        """
        if len(prices) < period:
            return None

        try:
            return round(sum(prices[-period:]) / period, 4)

        except Exception:
            return None

    def compute_volatility(self, prices: list[float]) -> Optional[float]:
        """
        Computes annualized volatility from daily closing prices.
        Returns decimal e.g. 0.25 = 25% annualized volatility.
        Returns None if fewer than 2 prices.
        """
        if len(prices) < 2:
            return None

        try:
            returns  = [(prices[i] - prices[i - 1]) / prices[i - 1]
                        for i in range(1, len(prices))]

            mean     = sum(returns) / len(returns)
            variance = sum((r - mean) ** 2 for r in returns) / len(returns)
            std_dev  = math.sqrt(variance)

            return round(std_dev * math.sqrt(252), 4)

        except Exception:
            return None

    def compute_max_drawdown(self, prices: list[float]) -> Optional[float]:
        """
        Computes maximum peak-to-trough decline in price history.
        Returns negative float e.g. -0.35 means 35% max drop.
        Returns None if fewer than 2 prices.
        """
        if len(prices) < 2:
            return None

        try:
            peak         = prices[0]
            max_drawdown = 0.0

            for price in prices:
                if price > peak:
                    peak = price
                drawdown = (price - peak) / peak
                if drawdown < max_drawdown:
                    max_drawdown = drawdown

            return round(max_drawdown, 4)

        except Exception:
            return None

    def compute_all(self, prices: list[float], volumes: list[float]) -> dict:
        """
        Main function called by MomentumTracker and RiskGuardian.
        Runs all indicators and returns a single result dict.
        Returns {} on failure.
        """
        try:
            rsi     = self.compute_rsi(prices)
            macd    = self.compute_macd(prices)
            sma_50  = self.compute_sma(prices, 50)
            sma_200 = self.compute_sma(prices, 200)

            current_price = prices[-1] if prices else None
            above_sma_50  = (current_price > sma_50)  if (current_price and sma_50)  else None
            above_sma_200 = (current_price > sma_200) if (current_price and sma_200) else None

            if len(volumes) >= 10:
                recent_vol   = sum(volumes[-5:]) / 5
                previous_vol = sum(volumes[-10:-5]) / 5
                if recent_vol > previous_vol * 1.1:
                    volume_trend = "increasing"
                elif recent_vol < previous_vol * 0.9:
                    volume_trend = "decreasing"
                else:
                    volume_trend = "flat"
            else:
                volume_trend = None

            # composite momentum score
            rsi_contribution  = ((rsi - 50) / 50) if rsi is not None else 0.0
            crossover         = macd.get("crossover") if macd else "neutral"
            macd_contribution = 0.3 if crossover == "bullish_cross" else (-0.3 if crossover == "bearish_cross" else 0.0)

            if above_sma_50 and above_sma_200:
                sma_contribution = 0.3
            elif not above_sma_50 and not above_sma_200:
                sma_contribution = -0.3
            else:
                sma_contribution = 0.0

            score = (rsi_contribution + macd_contribution + sma_contribution) / 3
            score = max(-1.0, min(1.0, score))

            return {
                "rsi_14":               rsi,
                "macd_signal":          crossover,
                "above_sma_50":         above_sma_50,
                "above_sma_200":        above_sma_200,
                "volume_trend":         volume_trend,
                "price_momentum_score": round(score, 4),
            }

        except Exception:
            return {}


engine = TechnicalEngine()




