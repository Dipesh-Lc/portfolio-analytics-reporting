"""Tests for factor model regression and attribution."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.attribution import interpret_factor_exposures
from src.analytics.factor_model import FactorModelResult, run_factor_regression


@pytest.fixture
def synthetic_factors():
    """500 days of synthetic Fama-French factors (decimal form)."""
    rng = np.random.default_rng(0)
    n = 500
    dates = pd.date_range("2022-01-03", periods=n, freq="B")
    return pd.DataFrame(
        {
            "date": dates,
            "mkt_rf": rng.normal(0.0003, 0.010, n),
            "smb": rng.normal(0.0001, 0.006, n),
            "hml": rng.normal(0.0001, 0.006, n),
            "rf": np.full(n, 0.00019),  # ~5% annual / 252
        }
    )


@pytest.fixture
def synthetic_portfolio(synthetic_factors):
    """
    Portfolio constructed as:
      R_p = RF + 1.1*Mkt-RF + 0.3*SMB - 0.2*HML + noise
    Known betas for test assertions.
    """
    rng = np.random.default_rng(1)
    f = synthetic_factors.set_index("date")
    noise = rng.normal(0, 0.002, len(f))
    port = f["rf"] + 1.1 * f["mkt_rf"] + 0.3 * f["smb"] - 0.2 * f["hml"] + noise
    port.name = "portfolio_return"
    return port


# --- FactorModelResult ---


def test_regression_returns_result(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert isinstance(result, FactorModelResult)


def test_regression_beta_mkt_close_to_1_1(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert abs(result.beta_mkt - 1.1) < 0.1


def test_regression_beta_smb_close_to_0_3(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert abs(result.beta_smb - 0.3) < 0.1


def test_regression_beta_hml_close_to_neg_0_2(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert abs(result.beta_hml - (-0.2)) < 0.1


def test_regression_r_squared_high(synthetic_portfolio, synthetic_factors):
    """With low noise, R^2 should be very high."""
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert result.r_squared > 0.80


def test_regression_n_obs_correct(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert result.n_obs == len(synthetic_portfolio)


def test_regression_r_squared_in_range(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    assert 0 <= result.r_squared <= 1


def test_regression_insufficient_overlap():
    # Factors and portfolio on completely different dates
    dates_a = pd.date_range("2020-01-01", periods=10, freq="B")
    dates_b = pd.date_range("2023-01-01", periods=10, freq="B")
    port = pd.Series(np.random.randn(10) * 0.01, index=dates_a)
    factors = pd.DataFrame(
        {
            "date": dates_b,
            "mkt_rf": np.random.randn(10) * 0.01,
            "smb": np.random.randn(10) * 0.005,
            "hml": np.random.randn(10) * 0.005,
            "rf": np.full(10, 0.0002),
        }
    )
    with pytest.raises(ValueError, match="Too few overlapping dates"):
        run_factor_regression(port, factors)


def test_result_to_dict(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    d = result.to_dict()
    assert isinstance(d, dict)
    assert "beta_mkt" in d
    assert "r_squared" in d


# --- Attribution interpretation ---


def test_interpret_returns_dict(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    attr = interpret_factor_exposures(result)
    assert isinstance(attr, dict)


def test_interpret_has_required_keys(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    attr = interpret_factor_exposures(result)
    for key in ["commentary", "style_summary", "attribution_table", "factor_loadings"]:
        assert key in attr


def test_interpret_commentary_is_nonempty(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    attr = interpret_factor_exposures(result)
    assert len(attr["commentary"]) > 0


def test_interpret_style_summary_is_string(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    attr = interpret_factor_exposures(result)
    assert isinstance(attr["style_summary"], str)
    assert len(attr["style_summary"]) > 0


def test_interpret_attribution_table_shape(synthetic_portfolio, synthetic_factors):
    result = run_factor_regression(synthetic_portfolio, synthetic_factors)
    attr = interpret_factor_exposures(result)
    # Should have Market, SMB, HML, Alpha = 4 rows
    assert len(attr["attribution_table"]) == 4
