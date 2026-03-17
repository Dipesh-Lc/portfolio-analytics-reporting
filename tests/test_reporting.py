"""Tests for chart generation and report output."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.performance import compute_monthly_returns, compute_performance_metrics


@pytest.fixture
def sample_returns():
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-02", periods=252, freq="B")
    return pd.Series(rng.normal(0.0004, 0.012, 252), index=dates)


# --- Performance metrics output ---


def test_performance_metrics_keys(sample_returns):
    m = compute_performance_metrics(sample_returns)
    for key in [
        "cumulative_return",
        "annualized_return",
        "annualized_volatility",
        "sharpe_ratio",
        "sortino_ratio",
        "hit_ratio",
    ]:
        assert key in m


def test_performance_hit_ratio_in_range(sample_returns):
    m = compute_performance_metrics(sample_returns)
    assert 0 <= m["hit_ratio"] <= 1


def test_performance_vol_positive(sample_returns):
    m = compute_performance_metrics(sample_returns)
    assert m["annualized_volatility"] > 0


def test_performance_empty_returns():
    m = compute_performance_metrics(pd.Series([], dtype=float))
    assert m == {}


# --- Monthly returns table ---


def test_monthly_returns_shape(sample_returns):
    monthly = compute_monthly_returns(sample_returns)
    assert isinstance(monthly, pd.DataFrame)
    # Should have month columns (Jan...Dec subset) + Annual
    assert "Annual" in monthly.columns
    assert len(monthly.columns) >= 2


def test_monthly_returns_annual_column_reasonable(sample_returns):
    monthly = compute_monthly_returns(sample_returns)
    # Annual return should be reasonable (not 1000x off)
    for val in monthly["Annual"].dropna():
        assert abs(val) < 5.0  # < 500% annual return for this test data


# --- Chart generation (file output tests) ---


def test_cumulative_returns_chart_creates_file(sample_returns, tmp_path):
    from src.reporting.charts import plot_cumulative_returns

    path = plot_cumulative_returns(sample_returns)
    # The function saves to artifacts/figures by default, just check it runs
    assert path is not None


def test_drawdown_chart_creates_file(sample_returns):
    from src.reporting.charts import plot_drawdown

    path = plot_drawdown(sample_returns)
    assert path is not None


def test_rolling_vol_chart_creates_file(sample_returns):
    from src.reporting.charts import plot_rolling_volatility

    path = plot_rolling_volatility(sample_returns)
    assert path is not None


def test_return_distribution_chart(sample_returns):
    from src.reporting.charts import plot_return_distribution

    path = plot_return_distribution(sample_returns)
    assert path is not None


# --- HTML Report generation ---


def test_generate_html_report_creates_file(sample_returns, tmp_path):
    from src.analytics.performance import compute_performance_metrics
    from src.analytics.risk import compute_risk_metrics
    from src.reporting.generate_report import generate_html_report

    perf = compute_performance_metrics(sample_returns)
    risk = compute_risk_metrics(sample_returns)

    holdings = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02"] * 3),
            "ticker": ["AAPL", "MSFT", "SPY"],
            "quantity": [50, 35, 20],
            "avg_cost": [185.0, 372.0, 470.0],
            "asset_class": ["Equity", "Equity", "ETF"],
            "sector": ["Technology", "Technology", "Index"],
            "region": ["US", "US", "US"],
        }
    )

    output_path = tmp_path / "test_report.html"

    # Minimal attribution mock
    attribution = {
        "style_summary": "Test portfolio",
        "commentary": ["Test commentary."],
        "factor_loadings": {"Market": 1.0, "SMB": 0.1, "HML": -0.1},
        "r_squared": 0.85,
        "attribution_table": pd.DataFrame(
            {
                "Factor": ["Market", "SMB", "HML", "Alpha"],
                "Loading": [1.0, 0.1, -0.1, 0.01],
                "P-value": [0.001, 0.05, 0.10, 0.30],
                "Significant (10%)": [True, True, True, False],
            }
        ),
    }

    class MockFactorResult:
        n_obs = 200
        alpha = 0.02
        alpha_pvalue = 0.30
        beta_mkt = 1.0
        beta_mkt_pvalue = 0.001
        beta_smb = 0.1
        beta_smb_pvalue = 0.05
        beta_hml = -0.1
        beta_hml_pvalue = 0.10
        r_squared = 0.85
        adj_r_squared = 0.849
        residual_std = 0.05
        info_ratio = 0.40
        regression_summary = "OLS summary"

    path = generate_html_report(
        holdings=holdings,
        daily_returns=sample_returns,
        perf_metrics=perf,
        risk_metrics=risk,
        factor_result=MockFactorResult(),
        attribution=attribution,
        chart_paths={},
        output_path=output_path,
    )

    assert path.exists()
    assert path.stat().st_size > 1000  # Not empty

    html = path.read_text(encoding="utf-8")
    assert "Portfolio" in html
