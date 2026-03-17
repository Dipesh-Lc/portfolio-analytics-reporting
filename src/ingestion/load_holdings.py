"""
Holdings ingestion module.
Reads and validates the portfolio holdings CSV file.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from src.utils.logger import get_logger
from src.utils.paths import HOLDINGS_FILE

logger = get_logger(__name__)

REQUIRED_COLUMNS = {"date", "ticker", "quantity", "avg_cost"}
VALID_ASSET_CLASSES = {"Equity", "ETF", "Bond", "Commodity", "Cash", "Other"}


def load_holdings(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load and validate portfolio holdings from CSV.

    Parameters
    ----------
    path : Path, optional
        Path to holdings CSV. Defaults to HOLDINGS_FILE.

    Returns
    -------
    pd.DataFrame
        Validated and normalized holdings DataFrame.
    """
    path = path or HOLDINGS_FILE

    if not Path(path).exists():
        raise FileNotFoundError(f"Holdings file not found: {path}")

    logger.info(f"Loading holdings from {path}")
    df = pd.read_csv(path, parse_dates=["date"])

    # Validate required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Holdings file missing required columns: {missing}")

    # Normalize tickers to uppercase
    df["ticker"] = df["ticker"].str.upper().str.strip()

    # Ensure date is proper datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

    # Fill optional columns with defaults
    if "asset_class" not in df.columns:
        df["asset_class"] = "Equity"
    if "sector" not in df.columns:
        df["sector"] = "Unknown"
    if "region" not in df.columns:
        df["region"] = "US"

    logger.info(f"Loaded {len(df)} holdings rows for {df['ticker'].nunique()} tickers")
    logger.debug(f"Tickers: {sorted(df['ticker'].unique().tolist())}")

    return df


def get_tickers(holdings: pd.DataFrame) -> list[str]:
    """Return sorted list of unique tickers from holdings."""
    return sorted(holdings["ticker"].unique().tolist())


def get_holdings_date(holdings: pd.DataFrame) -> pd.Timestamp:
    """Return the most recent holdings date."""
    return holdings["date"].max()
