"""
Build aligned prices panel from raw long-format price data.
Creates a wide matrix of adjusted close prices: rows=dates, columns=tickers.
"""

from typing import Optional

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

# Warn if a ticker has more than this fraction of missing trading days
MISSING_THRESHOLD = 0.10


def build_prices_panel(
    prices: pd.DataFrame,
    tickers: Optional[list[str]] = None,
    fill_method: str = "ffill",
    max_fill_days: int = 3,
) -> pd.DataFrame:
    """
    Build a clean wide adj_close panel from long-format price data.

    Parameters
    ----------
    prices : pd.DataFrame
        Long-format with columns: date, ticker, adj_close.
    tickers : list[str], optional
        Subset of tickers to include.
    fill_method : str
        'ffill' to forward-fill gaps (handles non-trading days/ETF lags).
    max_fill_days : int
        Maximum consecutive days to forward-fill.

    Returns
    -------
    pd.DataFrame
        Wide panel: index=date, columns=tickers, values=adj_close.
        Only includes trading days where at least one ticker has data.
    """
    if tickers:
        prices = prices[prices["ticker"].isin(tickers)]

    # Normalize dates
    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"]).dt.normalize()

    # Pivot to wide
    panel = prices.pivot_table(index="date", columns="ticker", values="adj_close", aggfunc="last")
    panel = panel.sort_index()

    # Report and handle missing data per ticker
    for ticker in panel.columns:
        missing_pct = panel[ticker].isna().mean()
        if missing_pct > MISSING_THRESHOLD:
            logger.warning(f"{ticker}: {missing_pct:.1%} missing adj_close in panel")

    # Forward-fill limited gaps (handles holidays, ETF non-trading days)
    if fill_method == "ffill":
        panel = panel.ffill(limit=max_fill_days)

    # Drop rows where ALL tickers are NaN (non-trading days)
    panel = panel.dropna(how="all")

    logger.info(
        f"Prices panel built: {len(panel)} dates x {len(panel.columns)} tickers "
        f"({panel.index.min().date()} to {panel.index.max().date()})"
    )
    return panel
