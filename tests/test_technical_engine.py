"""Tests for tools/technical_engine.py -- pure Python technical indicators."""

import inspect
import math

from tools.technical_engine import calc_macd, calc_rsi, calc_sma, calc_volatility

# ── RSI Tests ──────────────────────────────────────────────────────────────


class TestCalcRsi:
    def test_calc_rsi_basic(self):
        """RSI of a known price series returns a float in [0, 100]."""
        prices = [44.0 + i * 0.5 * ((-1) ** i) for i in range(50)]
        result = calc_rsi(prices)
        assert isinstance(result, float)
        assert 0.0 <= result <= 100.0

    def test_calc_rsi_all_up(self):
        """Monotonically increasing prices -> RSI near 100."""
        prices = [float(i) for i in range(1, 31)]
        result = calc_rsi(prices)
        assert result >= 99.0

    def test_calc_rsi_all_down(self):
        """Monotonically decreasing prices -> RSI near 0."""
        prices = [float(30 - i) for i in range(30)]
        result = calc_rsi(prices)
        assert result <= 1.0

    def test_calc_rsi_insufficient_data(self):
        """Fewer than period+1 prices -> returns 50.0."""
        result = calc_rsi([100.0, 101.0, 99.0], period=14)
        assert result == 50.0

    def test_calc_rsi_empty(self):
        """Empty list -> returns 50.0."""
        assert calc_rsi([]) == 50.0

    def test_calc_rsi_custom_period(self):
        """RSI with custom period works correctly."""
        prices = [float(i) for i in range(1, 20)]
        result = calc_rsi(prices, period=5)
        assert 0.0 <= result <= 100.0


# ── MACD Tests ─────────────────────────────────────────────────────────────


class TestCalcMacd:
    def test_calc_macd_basic(self):
        """MACD of a known series returns expected dict with numeric values."""
        prices = [float(100 + i * 0.5) for i in range(50)]
        result = calc_macd(prices)
        assert isinstance(result, dict)
        assert isinstance(result["macd_line"], float)
        assert isinstance(result["signal_line"], float)
        assert isinstance(result["histogram"], float)

    def test_calc_macd_insufficient_data(self):
        """Short list -> returns zeros dict."""
        result = calc_macd([1.0, 2.0, 3.0])
        assert result == {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0}

    def test_calc_macd_empty(self):
        """Empty list -> returns zeros dict."""
        result = calc_macd([])
        assert result == {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0}

    def test_calc_macd_keys(self):
        """Result has exactly macd_line, signal_line, histogram keys."""
        prices = [float(100 + i) for i in range(50)]
        result = calc_macd(prices)
        assert set(result.keys()) == {"macd_line", "signal_line", "histogram"}

    def test_calc_macd_uptrend_positive(self):
        """Strong uptrend should produce positive MACD line."""
        prices = [float(50 + i * 2) for i in range(50)]
        result = calc_macd(prices)
        assert result["macd_line"] > 0

    def test_calc_macd_histogram_consistency(self):
        """Histogram should equal macd_line - signal_line."""
        prices = [float(100 + i * 0.5 * ((-1) ** i)) for i in range(50)]
        result = calc_macd(prices)
        assert math.isclose(
            result["histogram"],
            result["macd_line"] - result["signal_line"],
            abs_tol=1e-10,
        )


# ── SMA Tests ──────────────────────────────────────────────────────────────


class TestCalcSma:
    def test_calc_sma_basic(self):
        """SMA of [10, 20, 30] period=3 -> 20.0."""
        assert calc_sma([10.0, 20.0, 30.0], period=3) == 20.0

    def test_calc_sma_partial(self):
        """Fewer prices than period -> average of available."""
        result = calc_sma([10.0, 20.0], period=5)
        assert result == 15.0

    def test_calc_sma_empty(self):
        """Empty list -> 0.0."""
        assert calc_sma([], period=5) == 0.0

    def test_calc_sma_single(self):
        """Single price -> returns that price."""
        assert calc_sma([42.0], period=10) == 42.0

    def test_calc_sma_uses_last_n(self):
        """SMA uses the last N prices, not the first N."""
        result = calc_sma([10.0, 20.0, 30.0, 40.0, 50.0], period=3)
        assert result == 40.0  # avg of [30, 40, 50]


# ── Volatility Tests ───────────────────────────────────────────────────────


class TestCalcVolatility:
    def test_calc_volatility_basic(self):
        """Known series returns a positive annualized vol."""
        prices = [100.0, 102.0, 99.0, 101.0, 103.0, 98.0, 100.0, 105.0]
        result = calc_volatility(prices)
        assert isinstance(result, float)
        assert result > 0.0

    def test_calc_volatility_constant(self):
        """Constant prices -> 0.0."""
        prices = [100.0] * 20
        assert calc_volatility(prices) == 0.0

    def test_calc_volatility_insufficient(self):
        """Fewer than 2 prices -> 0.0."""
        assert calc_volatility([100.0]) == 0.0

    def test_calc_volatility_empty(self):
        """Empty list -> 0.0."""
        assert calc_volatility([]) == 0.0

    def test_calc_volatility_annualization(self):
        """Volatility scales with sqrt of annualization period."""
        prices = [100.0 + i * 0.5 * ((-1) ** i) for i in range(50)]
        vol_252 = calc_volatility(prices, period=252)
        vol_52 = calc_volatility(prices, period=52)
        # vol_252 should be larger than vol_52 due to sqrt(period) scaling
        assert vol_252 > vol_52


# ── No External API Dependencies ──────────────────────────────────────────


class TestNoDeps:
    def test_no_external_api_deps(self):
        """Module imports contain no httpx/aiohttp/requests."""
        import tools.technical_engine as mod

        source = inspect.getsource(mod)
        for banned in ["httpx", "aiohttp", "requests"]:
            assert banned not in source, f"Found banned import: {banned}"
