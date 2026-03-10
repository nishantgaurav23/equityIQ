"""Tests for models/risk_calculator.py -- S4.2 Risk Calculator."""

import math

import numpy as np
import pytest

from models.risk_calculator import (
    calc_annualized_volatility,
    calc_beta,
    calc_max_drawdown,
    calc_position_size,
    calc_sharpe,
    calc_var_95,
)

# ---------------------------------------------------------------------------
# calc_beta
# ---------------------------------------------------------------------------


class TestCalcBeta:
    def test_known_values(self):
        # Stock moves 2x the market -> beta ~ 2.0
        market = [0.01, -0.02, 0.03, -0.01, 0.02, 0.01, -0.03, 0.02, 0.01, -0.01]
        stock = [0.02, -0.04, 0.06, -0.02, 0.04, 0.02, -0.06, 0.04, 0.02, -0.02]
        result = calc_beta(stock, market)
        assert abs(result - 2.0) < 0.01

    def test_identical_returns(self):
        returns = [0.01, -0.02, 0.03, -0.01, 0.02]
        result = calc_beta(returns, returns)
        assert abs(result - 1.0) < 0.001

    def test_empty_returns(self):
        assert calc_beta([], []) == 1.0

    def test_single_element(self):
        assert calc_beta([0.01], [0.01]) == 1.0

    def test_mismatched_lengths(self):
        with pytest.raises(ValueError):
            calc_beta([0.01, 0.02], [0.01])

    def test_zero_market_variance(self):
        # Constant market returns -> zero variance -> default 1.0
        stock = [0.01, -0.02, 0.03]
        market = [0.01, 0.01, 0.01]
        assert calc_beta(stock, market) == 1.0

    def test_negative_beta(self):
        # Stock moves opposite to market -> negative beta
        market = [0.01, -0.02, 0.03, -0.01, 0.02]
        stock = [-0.01, 0.02, -0.03, 0.01, -0.02]
        result = calc_beta(stock, market)
        assert result < 0

    def test_accepts_numpy_arrays(self):
        market = np.array([0.01, -0.02, 0.03, -0.01, 0.02])
        stock = np.array([0.02, -0.04, 0.06, -0.02, 0.04])
        result = calc_beta(stock, market)
        assert abs(result - 2.0) < 0.01


# ---------------------------------------------------------------------------
# calc_sharpe
# ---------------------------------------------------------------------------


class TestCalcSharpe:
    def test_positive_returns(self):
        # Consistently positive daily returns -> positive Sharpe
        returns = [0.001] * 252  # ~25.2% annual return
        result = calc_sharpe(returns, risk_free_rate=0.05)
        assert result > 0

    def test_empty_returns(self):
        assert calc_sharpe([]) == 0.0

    def test_single_element(self):
        assert calc_sharpe([0.01]) == 0.0

    def test_zero_std(self):
        # Constant returns -> zero std -> 0.0
        returns = [0.001, 0.001, 0.001, 0.001, 0.001]
        assert calc_sharpe(returns) == 0.0

    def test_known_value(self):
        # Hand-calculated: daily_rf = 0.05/252 ≈ 0.000198
        # mean daily return = 0.001, std = known
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)
        mean_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        daily_rf = 0.05 / 252
        expected = (mean_r - daily_rf) / std_r * math.sqrt(252)
        result = calc_sharpe(returns.tolist(), risk_free_rate=0.05)
        assert abs(result - expected) < 0.01

    def test_default_risk_free_rate(self):
        returns = [0.002] * 100
        # Should use 0.05 default
        result = calc_sharpe(returns)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# calc_var_95
# ---------------------------------------------------------------------------


class TestCalcVar95:
    def test_known_distribution(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 10000).tolist()
        result = calc_var_95(returns)
        # 5th percentile of N(0, 0.02) ≈ -0.0329
        assert -0.04 < result < -0.02

    def test_empty(self):
        assert calc_var_95([]) == 0.0

    def test_single_element(self):
        assert calc_var_95([-0.05]) == -0.05

    def test_all_positive(self):
        returns = [0.01, 0.02, 0.03, 0.04, 0.05]
        result = calc_var_95(returns)
        # Even all-positive returns have a 5th percentile
        assert result > 0  # still positive since all returns are positive

    def test_accepts_numpy(self):
        returns = np.array([-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03])
        result = calc_var_95(returns)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# calc_max_drawdown
# ---------------------------------------------------------------------------


class TestCalcMaxDrawdown:
    def test_known_drawdown(self):
        # Peak at 100, drops to 50 (50% drawdown), recovers to 80
        prices = [100, 110, 105, 50, 60, 80]
        result = calc_max_drawdown(prices)
        # Max drawdown from 110 to 50 = (50 - 110) / 110 ≈ -0.5454
        assert abs(result - (-60 / 110)) < 0.01

    def test_monotonic_up(self):
        prices = [100, 110, 120, 130, 140]
        assert calc_max_drawdown(prices) == 0.0

    def test_empty(self):
        assert calc_max_drawdown([]) == 0.0

    def test_single_element(self):
        assert calc_max_drawdown([100]) == 0.0

    def test_monotonic_down(self):
        # Continuous decline from 100 to 50
        prices = [100, 90, 80, 70, 60, 50]
        result = calc_max_drawdown(prices)
        assert abs(result - (-0.5)) < 0.01

    def test_multiple_drawdowns(self):
        # Two drawdowns: first -20%, second -30%
        prices = [100, 80, 100, 70, 90]
        result = calc_max_drawdown(prices)
        # Largest drawdown: 100 -> 70 = -30%
        assert abs(result - (-0.30)) < 0.01

    def test_accepts_numpy(self):
        prices = np.array([100.0, 90.0, 80.0, 95.0])
        result = calc_max_drawdown(prices)
        assert result < 0


# ---------------------------------------------------------------------------
# calc_position_size
# ---------------------------------------------------------------------------


class TestCalcPositionSize:
    def test_normal_volatility(self):
        # vol = 0.25, risk = 0.02 -> 0.02 / 0.25 = 0.08
        result = calc_position_size(0.25)
        assert abs(result - 0.08) < 0.001

    def test_capped_at_max(self):
        # Very low vol -> would be large position -> capped at 0.10
        result = calc_position_size(0.01)
        assert result == 0.10

    def test_zero_volatility(self):
        assert calc_position_size(0.0) == 0.10

    def test_negative_volatility(self):
        assert calc_position_size(-0.5) == 0.10

    def test_high_volatility(self):
        # vol = 1.0, risk = 0.02 -> 0.02
        result = calc_position_size(1.0)
        assert abs(result - 0.02) < 0.001

    def test_custom_max_position(self):
        result = calc_position_size(0.25, max_position=0.05)
        assert result <= 0.05

    def test_custom_max_portfolio_risk(self):
        result = calc_position_size(0.25, max_portfolio_risk=0.05)
        assert abs(result - 0.10) < 0.001  # 0.05 / 0.25 = 0.20, capped at 0.10

    def test_never_exceeds_hard_cap(self):
        # Even with custom max_position, default hard cap still applies through caller
        for vol in [0.001, 0.01, 0.1, 0.5, 1.0]:
            result = calc_position_size(vol)
            assert result <= 0.10


# ---------------------------------------------------------------------------
# calc_annualized_volatility
# ---------------------------------------------------------------------------


class TestCalcAnnualizedVolatility:
    def test_known_value(self):
        np.random.seed(42)
        returns = np.random.normal(0, 0.01, 252).tolist()
        daily_std = np.std(returns, ddof=1)
        expected = daily_std * math.sqrt(252)
        result = calc_annualized_volatility(returns)
        assert abs(result - expected) < 0.001

    def test_empty(self):
        assert calc_annualized_volatility([]) == 0.0

    def test_single_element(self):
        assert calc_annualized_volatility([0.01]) == 0.0

    def test_zero_variance(self):
        returns = [0.01, 0.01, 0.01]
        assert calc_annualized_volatility(returns) == 0.0

    def test_accepts_numpy(self):
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.01])
        result = calc_annualized_volatility(returns)
        assert result > 0
