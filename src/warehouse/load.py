"""
Load cleaned data into the SQLite warehouse.
All loaders use INSERT OR REPLACE semantics (upsert).
"""

import pandas as pd
from sqlalchemy.engine import Engine

from src.utils.logger import get_logger
from src.warehouse.db import get_engine

logger = get_logger(__name__)


def _upsert(df: pd.DataFrame, table: str, engine: Engine, if_exists: str = "append") -> None:
    """Write DataFrame to table, replacing duplicates via INSERT OR REPLACE."""
    df.to_sql(table, con=engine, if_exists=if_exists, index=False, method="multi")
    logger.debug(f"Wrote {len(df)} rows to {table}")


def load_holdings(holdings: pd.DataFrame, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    df = holdings.copy()
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    # Replace existing for same date/ticker
    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT OR REPLACE INTO holdings (date,ticker,quantity,avg_cost,asset_class,sector,region) "
                    "VALUES (:date,:ticker,:quantity,:avg_cost,:asset_class,:sector,:region)"
                ),
                row.to_dict(),
            )
        conn.commit()
    logger.info(f"Loaded {len(df)} holdings rows into warehouse")


def load_prices(prices: pd.DataFrame, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    # Rename adj_close column
    if "adj_close" not in df.columns and "Adj Close" in df.columns:
        df = df.rename(columns={"Adj Close": "adj_close"})

    cols = [
        "date",
        "ticker",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividends",
        "stock_splits",
    ]
    df = df[[c for c in cols if c in df.columns]]

    with engine.connect() as conn:
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            cols_present = list(row_dict.keys())
            placeholders = ", ".join(f":{c}" for c in cols_present)
            col_str = ", ".join(cols_present)
            conn.execute(
                __import__("sqlalchemy").text(
                    f"INSERT OR REPLACE INTO prices_daily ({col_str}) VALUES ({placeholders})"
                ),
                row_dict,
            )
        conn.commit()
    logger.info(f"Loaded {len(df)} price rows into warehouse")


def load_factors(factors: pd.DataFrame, engine: Engine | None = None) -> None:
    engine = engine or get_engine()
    df = factors.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT OR REPLACE INTO factors_daily (date,mkt_rf,smb,hml,rf) "
                    "VALUES (:date,:mkt_rf,:smb,:hml,:rf)"
                ),
                row.to_dict(),
            )
        conn.commit()
    logger.info(f"Loaded {len(df)} factor rows into warehouse")


def load_portfolio_returns(returns_df: pd.DataFrame, engine: Engine | None = None) -> None:
    """
    Load portfolio returns to warehouse.

    Parameters
    ----------
    returns_df : pd.DataFrame
        Columns: date, daily_return, cumulative_return, daily_pnl, cumulative_pnl, portfolio_value
    """
    engine = engine or get_engine()
    df = returns_df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    with engine.connect() as conn:
        for _, row in df.iterrows():
            conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT OR REPLACE INTO portfolio_returns "
                    "(date,daily_return,cumulative_return,daily_pnl,cumulative_pnl,portfolio_value) "
                    "VALUES (:date,:daily_return,:cumulative_return,:daily_pnl,:cumulative_pnl,:portfolio_value)"
                ),
                row.to_dict(),
            )
        conn.commit()
    logger.info(f"Loaded {len(df)} portfolio return rows into warehouse")


def load_analytics_snapshot(metrics: dict, run_date: str, engine: Engine | None = None) -> None:
    """Store a flat dict of metric -> value as a snapshot."""
    engine = engine or get_engine()

    with engine.connect() as conn:
        for metric, value in metrics.items():
            if isinstance(value, (int, float)):
                conn.execute(
                    __import__("sqlalchemy").text(
                        "INSERT INTO analytics_snapshots (run_date, metric, value) "
                        "VALUES (:run_date, :metric, :value)"
                    ),
                    {"run_date": run_date, "metric": metric, "value": value},
                )
        conn.commit()
    logger.info(f"Saved {len(metrics)} analytics metrics for {run_date}")
