"""Tests for return computation logic."""

import numpy as np
import pandas as pd
import pytest

from src.processing.returns import (
    annualized_return,
    compute_asset_returns,
    compute_cumulative_returns,
    compute_portfolio_returns,
)


@pytest.fixture
def simple_panel():
    """3 tickers, 10 days, steady 1% daily gain for AAPL and MSFT, flat SPY."""
    dates = pd.date_range("2024-01-02", periods=10, freq="B")
    data = {
        "AAPL": 100 * (1.01 ** np.arange(10)),
        "MSFT": 200 * (1.02 ** np.arange(10)),
        "SPY": np.ones(10) * 450,
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def equal_weights(simple_panel):
    """Equal weights across all 3 tickers."""
    w = pd.DataFrame(
        1 / 3,
        index=simple_panel.index[1:],  # Returns have one fewer row
        columns=simple_panel.columns,
    )
    return w


def test_compute_asset_returns_shape(simple_panel):
    r = compute_asset_returns(simple_panel)
    assert r.shape == (9, 3)  # 10 prices -> 9 returns


def test_compute_asset_returns_values(simple_panel):
    r = compute_asset_returns(simple_panel)
    # AAPL daily return should be ~1%
    assert abs(r["AAPL"].mean() - 0.01) < 1e-10


def test_compute_asset_returns_spy_flat(simple_panel):
    r = compute_asset_returns(simple_panel)
    # SPY is flat -> 0 returns
    assert (r["SPY"] == 0).all()


def test_compute_asset_returns_log_method(simple_panel):
    r = compute_asset_returns(simple_panel, method="log")
    assert r.shape == (9, 3)
    # Log returns for 1% price change ~ 0.00995
    assert abs(r["AAPL"].mean() - np.log(1.01)) < 1e-10


def test_compute_asset_returns_invalid_method(simple_panel):
    with pytest.raises(ValueError):
        compute_asset_returns(simple_panel, method="invalid")


def test_compute_portfolio_returns(simple_panel, equal_weights):
    asset_r = compute_asset_returns(simple_panel)
    port_r = compute_portfolio_returns(asset_r, equal_weights)

    assert isinstance(port_r, pd.Series)
    assert len(port_r) == 9
    assert port_r.name == "portfolio_return"


def test_compute_portfolio_returns_all_cash(simple_panel):
    """Zero weights -> zero portfolio return."""
    asset_r = compute_asset_returns(simple_panel)
    zero_w = pd.DataFrame(0.0, index=asset_r.index, columns=simple_panel.columns)
    port_r = compute_portfolio_returns(asset_r, zero_w)
    assert (port_r == 0).all()


def test_compute_cumulative_returns():
    r = pd.Series([0.01, 0.02, -0.01, 0.01])
    cum = compute_cumulative_returns(r)
    expected_final = (1.01 * 1.02 * 0.99 * 1.01) - 1
    assert abs(cum.iloc[-1] - expected_final) < 1e-12


def test_annualized_return_positive():
    # 252 days of 0.01% daily = ~2.5% annual
    r = pd.Series([0.0001] * 252)
    ann = annualized_return(r, trading_days=252)
    expected = (1.0001**252) - 1
    assert abs(ann - expected) < 1e-10


def test_annualized_return_empty():
    r = pd.Series([], dtype=float)
    assert np.isnan(annualized_return(r))


def test_cumulative_return_is_positive_for_gains():
    r = pd.Series([0.01] * 10)
    cum = compute_cumulative_returns(r)
    assert cum.iloc[-1] > 0
    assert (cum.diff().dropna() > 0).all()
