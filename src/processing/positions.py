"""
Portfolio position and weight computation.
Converts holdings + prices into daily market values and weights.
"""

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def compute_market_values(
    holdings: pd.DataFrame,
    prices_panel: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute daily market value for each position.

    Parameters
    ----------
    holdings : pd.DataFrame
        Holdings with columns: ticker, quantity.
    prices_panel : pd.DataFrame
        Wide adj_close panel: index=date, columns=tickers.

    Returns
    -------
    pd.DataFrame
        Wide daily market values: index=date, columns=tickers.
    """
    # Use last holdings snapshot (static positions in v1)
    latest = holdings.sort_values("date").drop_duplicates("ticker", keep="last")
    qty = latest.set_index("ticker")["quantity"]

    # Only include tickers we have prices for
    common = [t for t in qty.index if t in prices_panel.columns]
    missing = [t for t in qty.index if t not in prices_panel.columns]
    if missing:
        logger.warning(f"No prices for tickers (excluded from positions): {missing}")

    mkt_values = prices_panel[common].multiply(qty[common], axis="columns")
    logger.info(f"Market values computed for {len(common)} tickers over {len(mkt_values)} days")
    return mkt_values


def compute_portfolio_weights(market_values: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily portfolio weights from market values.

    Parameters
    ----------
    market_values : pd.DataFrame
        Wide daily market values.

    Returns
    -------
    pd.DataFrame
        Daily portfolio weights (each row sums to 1).
    """
    row_sums = market_values.sum(axis=1)
    weights = market_values.div(row_sums, axis=0)
    return weights


def compute_portfolio_value_series(market_values: pd.DataFrame) -> pd.Series:
    """Total portfolio value (NAV) per day."""
    return market_values.sum(axis=1).rename("portfolio_value")


def compute_pnl(
    market_values: pd.DataFrame,
    holdings: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute daily and cumulative P&L.

    Returns
    -------
    pd.DataFrame with columns: daily_pnl, cumulative_pnl, portfolio_value
    """
    portfolio_value = compute_portfolio_value_series(market_values)

    # Cost basis
    latest = holdings.sort_values("date").drop_duplicates("ticker", keep="last")
    latest["cost_basis"] = latest["quantity"] * latest["avg_cost"]

    common = [t for t in latest["ticker"] if t in market_values.columns]
    total_cost = latest.set_index("ticker").loc[common, "cost_basis"].sum()

    daily_pnl = portfolio_value.diff()
    daily_pnl.iloc[0] = portfolio_value.iloc[0] - total_cost

    cumulative_pnl = portfolio_value - total_cost

    result = pd.DataFrame(
        {
            "portfolio_value": portfolio_value,
            "daily_pnl": daily_pnl,
            "cumulative_pnl": cumulative_pnl,
        }
    )
    return result


def compute_sector_weights(
    holdings: pd.DataFrame,
    market_values: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute sector-level weights for the latest date.

    Returns
    -------
    pd.DataFrame
        Columns: sector, market_value, weight
    """
    latest = holdings.drop_duplicates("ticker", keep="last").set_index("ticker")
    latest_mv = market_values.iloc[-1]
    total = latest_mv.sum()

    rows = []
    for ticker, mv in latest_mv.items():
        sector = latest.loc[ticker, "sector"] if ticker in latest.index else "Unknown"
        rows.append({"ticker": ticker, "sector": sector, "market_value": mv, "weight": mv / total})

    df = pd.DataFrame(rows)
    sector_agg = (
        df.groupby("sector")
        .agg(market_value=("market_value", "sum"), weight=("weight", "sum"))
        .reset_index()
        .sort_values("weight", ascending=False)
    )
    return sector_agg
