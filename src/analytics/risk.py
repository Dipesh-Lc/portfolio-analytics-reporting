"""
Risk analytics: volatility, drawdown, VaR, CVaR, concentration.
"""

import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

TRADING_DAYS = 252


def compute_max_drawdown(daily_returns: pd.Series) -> float:
    """
    Compute maximum drawdown from daily return series.

    Returns
    -------
    float
        Max drawdown as a negative decimal (e.g., -0.25 = -25%).
    """
    cumulative = (1 + daily_returns.dropna()).cumprod()
    rolling_max = cumulative.cummax()
    drawdown = cumulative / rolling_max - 1
    return float(drawdown.min())


def compute_drawdown_series(daily_returns: pd.Series) -> pd.Series:
    """
    Compute rolling drawdown series (underwater curve).

    Returns
    -------
    pd.Series
        Drawdown at each date (0 = at high water mark, -0.2 = 20% below peak).
    """
    cumulative = (1 + daily_returns.dropna()).cumprod()
    rolling_max = cumulative.cummax()
    return (cumulative / rolling_max - 1).rename("drawdown")


def compute_var_historical(
    daily_returns: pd.Series,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """
    Compute historical Value at Risk (VaR).

    The most transparent VaR method: uses empirical return distribution.
    No distribution assumptions.

    Parameters
    ----------
    daily_returns : pd.Series
        Daily portfolio returns.
    confidence : float
        Confidence level (e.g., 0.95 for 95% VaR).
    horizon_days : int
        Holding period in days. Scaled by sqrt(horizon) for multi-day.

    Returns
    -------
    float
        VaR as a positive loss magnitude (e.g., 0.02 = 2% loss at confidence level).
    """
    r = daily_returns.dropna()
    quantile_level = 1 - confidence
    var_1d = float(-np.percentile(r, quantile_level * 100))

    # Scale to horizon (square-root-of-time rule)
    var = var_1d * np.sqrt(horizon_days)

    logger.debug(
        f"Historical VaR({confidence:.0%}, {horizon_days}d): {var:.4f} " f"({var:.2%} of portfolio)"
    )
    return var


def compute_cvar_historical(
    daily_returns: pd.Series,
    confidence: float = 0.95,
) -> float:
    """
    Compute historical Conditional VaR (CVaR / Expected Shortfall).

    CVaR = expected loss given that the loss exceeds VaR.
    More conservative than VaR; accounts for tail severity.

    Returns
    -------
    float
        CVaR as a positive loss magnitude.
    """
    r = daily_returns.dropna()
    quantile_level = 1 - confidence
    threshold = np.percentile(r, quantile_level * 100)
    tail_losses = r[r <= threshold]

    if len(tail_losses) == 0:
        return compute_var_historical(r, confidence)

    cvar = float(-tail_losses.mean())
    logger.debug(f"Historical CVaR({confidence:.0%}): {cvar:.4f}")
    return cvar


def compute_risk_metrics(
    daily_returns: pd.Series,
    confidence: float = 0.95,
    trading_days: int = TRADING_DAYS,
    risk_free_annual: float = 0.05,
) -> dict:
    """
    Compute full risk metrics suite.

    Returns
    -------
    dict
        Risk metrics dictionary.
    """
    r = daily_returns.dropna()
    n = len(r)

    if n < 10:
        logger.warning("Too few observations for reliable risk metrics")
        return {}

    rf_daily = (1 + risk_free_annual) ** (1 / trading_days) - 1

    # Volatility
    daily_vol = float(r.std())
    ann_vol = float(daily_vol * np.sqrt(trading_days))

    # Downside deviation (below risk-free rate)
    downside = r[r < rf_daily]
    downside_dev = float(downside.std() * np.sqrt(trading_days)) if len(downside) > 1 else np.nan

    # Drawdown
    max_dd = compute_max_drawdown(r)
    dd_series = compute_drawdown_series(r)
    avg_dd = float(dd_series[dd_series < 0].mean()) if (dd_series < 0).any() else 0.0

    # VaR and CVaR
    var_95 = compute_var_historical(r, confidence=confidence, horizon_days=1)
    cvar_95 = compute_cvar_historical(r, confidence=confidence)

    # Skewness and kurtosis (tail shape indicators)
    from scipy import stats

    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r))  # excess kurtosis

    metrics = {
        "daily_volatility": daily_vol,
        "annualized_volatility": ann_vol,
        "downside_deviation_annual": downside_dev,
        "max_drawdown": max_dd,
        "average_drawdown": avg_dd,
        f"var_{int(confidence*100)}_1d": var_95,
        f"cvar_{int(confidence*100)}_1d": cvar_95,
        "return_skewness": skew,
        "return_excess_kurtosis": kurt,
        "var_confidence": confidence,
    }

    logger.info(
        f"Risk: ann_vol={ann_vol:.2%}, max_dd={max_dd:.2%}, "
        f"VaR95={var_95:.2%}, CVaR95={cvar_95:.2%}"
    )
    return metrics
