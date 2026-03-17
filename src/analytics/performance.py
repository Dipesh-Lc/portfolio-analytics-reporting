"""
Performance analytics: cumulative returns, Sharpe, Sortino, hit ratio, rolling metrics.
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

TRADING_DAYS = 252


def compute_performance_metrics(
    daily_returns: pd.Series,
    risk_free_annual: float = 0.05,
    trading_days: int = TRADING_DAYS,
) -> dict:
    """
    Compute a full suite of portfolio performance metrics.

    Parameters
    ----------
    daily_returns : pd.Series
        Daily portfolio return series.
    risk_free_annual : float
        Annual risk-free rate (decimal). Used for Sharpe/Sortino.
    trading_days : int
        Trading days per year for annualization.

    Returns
    -------
    dict
        Performance metrics dictionary.
    """
    r = daily_returns.dropna()
    n = len(r)

    if n < 2:
        logger.warning("Too few return observations for meaningful performance metrics")
        return {}

    # Risk-free daily rate
    rf_daily = (1 + risk_free_annual) ** (1 / trading_days) - 1

    # Cumulative and annualized return
    cum_return = float((1 + r).prod() - 1)
    ann_return = float((1 + r).prod() ** (trading_days / n) - 1)

    # Volatility
    ann_vol = float(r.std() * np.sqrt(trading_days))

    # Sharpe ratio
    excess = r - rf_daily
    sharpe = (
        float(excess.mean() / excess.std() * np.sqrt(trading_days)) if excess.std() > 0 else np.nan
    )

    # Sortino ratio (downside deviation)
    downside = r[r < rf_daily] - rf_daily
    downside_std = float(np.sqrt((downside**2).mean()) * np.sqrt(trading_days))
    sortino = float((ann_return - risk_free_annual) / downside_std) if downside_std > 0 else np.nan

    # Hit ratio (% of positive return days)
    hit_ratio = float((r > 0).mean())

    # Best / worst days
    best_day = float(r.max())
    worst_day = float(r.min())

    # Calmar ratio
    from src.analytics.risk import compute_max_drawdown

    max_dd = compute_max_drawdown(r)
    calmar = float(ann_return / abs(max_dd)) if max_dd != 0 else np.nan

    metrics = {
        "cumulative_return": cum_return,
        "annualized_return": ann_return,
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "calmar_ratio": calmar,
        "hit_ratio": hit_ratio,
        "best_day_return": best_day,
        "worst_day_return": worst_day,
        "total_trading_days": n,
        "risk_free_rate_annual": risk_free_annual,
    }

    logger.info(
        f"Performance: cum_return={cum_return:.2%}, ann_return={ann_return:.2%}, "
        f"sharpe={sharpe:.2f}, max_dd={max_dd:.2%}"
    )
    return metrics


def compute_rolling_metrics(
    daily_returns: pd.Series,
    window: int = 63,
    trading_days: int = TRADING_DAYS,
    risk_free_annual: float = 0.05,
) -> pd.DataFrame:
    """
    Compute rolling performance metrics over a rolling window.

    Returns
    -------
    pd.DataFrame
        Columns: rolling_return, rolling_vol, rolling_sharpe
    """
    r = daily_returns.dropna()
    rf_daily = (1 + risk_free_annual) ** (1 / trading_days) - 1

    rolling_vol = r.rolling(window).std() * np.sqrt(trading_days)
    rolling_return = r.rolling(window).apply(
        lambda x: (1 + x).prod() ** (trading_days / len(x)) - 1
    )
    rolling_excess = (r - rf_daily).rolling(window)
    rolling_sharpe = rolling_excess.mean() / (r.rolling(window).std()) * np.sqrt(trading_days)

    result = pd.DataFrame(
        {
            "rolling_return": rolling_return,
            "rolling_vol": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
        }
    )
    return result


def compute_monthly_returns(daily_returns: pd.Series) -> pd.DataFrame:
    """
    Aggregate daily returns into a monthly returns table.

    Returns
    -------
    pd.DataFrame
        Pivot table: rows=year, columns=month abbreviation, values=monthly return.
    """
    r = daily_returns.dropna().copy()
    r.index = pd.to_datetime(r.index)

    monthly = r.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    monthly.index = monthly.index.to_period("M")

    df = monthly.reset_index()
    df.columns = ["period", "return"]
    df["year"] = df["period"].dt.year
    df["month"] = df["period"].dt.month

    pivot = df.pivot(index="year", columns="month", values="return")
    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    pivot.columns = [month_names.get(m, str(m)) for m in pivot.columns]
    pivot["Annual"] = df.groupby("year")["return"].apply(lambda r: (1 + r).prod() - 1).values

    return pivot
