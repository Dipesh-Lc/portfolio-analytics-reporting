"""Tests for risk metrics: drawdown, VaR, CVaR, and full suite."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.risk import (
    compute_cvar_historical,
    compute_drawdown_series,
    compute_max_drawdown,
    compute_risk_metrics,
    compute_var_historical,
)


@pytest.fixture
def flat_returns():
    """Zero returns — no drawdown, zero vol."""
    return pd.Series(np.zeros(100))


@pytest.fixture
def steady_gains():
    """1% daily gain — monotonically rising, no drawdown."""
    return pd.Series([0.01] * 100)


@pytest.fixture
def known_drawdown():
    """
    Returns that create a known drawdown pattern:
    +10%, +10%, -20%, +10%, +10%
    Peak after day 2 → drawdown of -20% / 1.21 ≈ -16.5% at day 3.
    """
    return pd.Series([0.10, 0.10, -0.20, 0.10, 0.10])


@pytest.fixture
def normal_returns():
    """100 normally distributed returns, seeded for reproducibility."""
    rng = np.random.default_rng(42)
    return pd.Series(rng.normal(0.0005, 0.015, 500))


# --- Max Drawdown ---


def test_max_drawdown_no_drawdown(steady_gains):
    dd = compute_max_drawdown(steady_gains)
    assert dd == pytest.approx(0.0, abs=1e-10)


def test_max_drawdown_flat(flat_returns):
    dd = compute_max_drawdown(flat_returns)
    assert dd == pytest.approx(0.0, abs=1e-10)


def test_max_drawdown_known(known_drawdown):
    dd = compute_max_drawdown(known_drawdown)
    # Returns: +10%, +10%, -20%, +10%, +10%
    # NAV path: 1.0 → 1.10 → 1.21 → 0.968 → 1.065 → 1.171
    # Peak at day 2 = 1.21; trough at day 3 = 0.968
    # Max drawdown = 0.968 / 1.21 - 1 = -0.20 exactly
    assert dd < 0
    assert abs(dd - (-0.20)) < 0.001


def test_max_drawdown_is_negative_for_any_loss():
    r = pd.Series([0.05, -0.10, 0.05])
    assert compute_max_drawdown(r) < 0


def test_max_drawdown_returns_float(steady_gains):
    assert isinstance(compute_max_drawdown(steady_gains), float)


# --- Drawdown Series ---


def test_drawdown_series_length(steady_gains):
    dd = compute_drawdown_series(steady_gains)
    assert len(dd) == len(steady_gains)


def test_drawdown_series_all_zero_for_monotonic_gains(steady_gains):
    dd = compute_drawdown_series(steady_gains)
    assert (dd >= -1e-10).all()


def test_drawdown_series_non_positive(normal_returns):
    dd = compute_drawdown_series(normal_returns)
    assert (dd <= 1e-10).all()


def test_drawdown_series_min_equals_max_drawdown(normal_returns):
    dd_series = compute_drawdown_series(normal_returns)
    max_dd = compute_max_drawdown(normal_returns)
    assert abs(dd_series.min() - max_dd) < 1e-10


# --- Historical VaR ---


def test_var_is_positive(normal_returns):
    var = compute_var_historical(normal_returns)
    assert var > 0


def test_var_95_less_than_var_99(normal_returns):
    var_95 = compute_var_historical(normal_returns, confidence=0.95)
    var_99 = compute_var_historical(normal_returns, confidence=0.99)
    assert var_99 > var_95


def test_var_scales_with_horizon(normal_returns):
    var_1d = compute_var_historical(normal_returns, horizon_days=1)
    var_10d = compute_var_historical(normal_returns, horizon_days=10)
    assert abs(var_10d - var_1d * np.sqrt(10)) < 1e-10


def test_var_consistent_with_percentile(normal_returns):
    r = normal_returns.dropna()
    var = compute_var_historical(r, confidence=0.95)
    # 5th percentile loss
    empirical = -np.percentile(r, 5)
    assert abs(var - empirical) < 1e-10


# --- CVaR ---


def test_cvar_greater_than_var(normal_returns):
    var = compute_var_historical(normal_returns, confidence=0.95)
    cvar = compute_cvar_historical(normal_returns, confidence=0.95)
    assert cvar >= var


def test_cvar_is_positive(normal_returns):
    cvar = compute_cvar_historical(normal_returns)
    assert cvar > 0


# --- Full risk suite ---


def test_risk_metrics_returns_dict(normal_returns):
    metrics = compute_risk_metrics(normal_returns)
    assert isinstance(metrics, dict)
    assert len(metrics) > 0


def test_risk_metrics_has_required_keys(normal_returns):
    metrics = compute_risk_metrics(normal_returns)
    required = ["annualized_volatility", "max_drawdown", "var_95_1d", "cvar_95_1d"]
    for key in required:
        assert key in metrics, f"Missing key: {key}"


def test_risk_metrics_max_drawdown_non_positive(normal_returns):
    metrics = compute_risk_metrics(normal_returns)
    assert metrics["max_drawdown"] <= 0


def test_risk_metrics_vol_positive(normal_returns):
    metrics = compute_risk_metrics(normal_returns)
    assert metrics["annualized_volatility"] > 0


def test_risk_metrics_insufficient_data():
    r = pd.Series([0.01, 0.02])
    result = compute_risk_metrics(r)
    assert result == {}
