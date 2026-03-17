"""
Asset and portfolio return computation.
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def compute_asset_returns(
    panel: pd.DataFrame,
    method: str = "simple",
) -> pd.DataFrame:
    """
    Compute daily returns for each ticker from the adj_close panel.

    Parameters
    ----------
    panel : pd.DataFrame
        Wide adj_close panel: index=date, columns=tickers.
    method : str
        'simple' = (P_t / P_{t-1}) - 1
        'log' = ln(P_t / P_{t-1})

    Returns
    -------
    pd.DataFrame
        Daily returns panel, same shape as input (first row NaN).
    """
    if method == "simple":
        returns = panel.pct_change()
    elif method == "log":
        returns = np.log(panel / panel.shift(1))
    else:
        raise ValueError(f"Unknown return method: {method}. Use 'simple' or 'log'.")

    # Drop first row (all NaN)
    returns = returns.iloc[1:]

    logger.info(f"Computed {method} returns: {len(returns)} days x {len(returns.columns)} tickers")
    return returns


def compute_portfolio_returns(
    asset_returns: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.Series:
    """
    Compute daily portfolio return as the weighted sum of asset returns.

    Parameters
    ----------
    asset_returns : pd.DataFrame
        Daily asset returns: index=date, columns=tickers.
    weights : pd.DataFrame
        Daily portfolio weights: index=date, columns=tickers.
        Rows need not sum to exactly 1 if cash is excluded.

    Returns
    -------
    pd.Series
        Daily portfolio return series.
    """
    # Align dates
    common_dates = asset_returns.index.intersection(weights.index)
    r = asset_returns.loc[common_dates]
    w = weights.loc[common_dates]

    # Common tickers
    common_tickers = r.columns.intersection(w.columns)
    r = r[common_tickers]
    w = w[common_tickers]

    # Daily portfolio return = sum(w_i * r_i)
    port_returns = (r * w).sum(axis=1)
    port_returns.name = "portfolio_return"

    logger.info(
        f"Portfolio returns computed: {len(port_returns)} days, "
        f"mean daily return = {port_returns.mean():.4f}"
    )
    return port_returns


def compute_cumulative_returns(daily_returns: pd.Series) -> pd.Series:
    """Compute cumulative return series from daily returns."""
    return (1 + daily_returns).cumprod() - 1


def annualized_return(daily_returns: pd.Series, trading_days: int = 252) -> float:
    """Compute annualized return from daily return series."""
    n = len(daily_returns)
    if n == 0:
        return np.nan
    total = (1 + daily_returns).prod()
    return float(total ** (trading_days / n) - 1)
