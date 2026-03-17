"""
Holdings cleaning and normalization utilities.
Applied after initial ingestion and before downstream processing.
"""

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

KNOWN_ASSET_CLASSES = {"Equity", "ETF", "Bond", "Commodity", "Cash", "Other"}


def clean_holdings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply standard cleaning rules to raw holdings.

    Steps:
    1. Standardize ticker casing and strip whitespace
    2. Normalize date column
    3. Coerce numeric columns
    4. Fill missing optional columns with defaults
    5. Deduplicate on (date, ticker)
    6. Sort by date, then ticker

    Parameters
    ----------
    df : pd.DataFrame
        Raw holdings as loaded from CSV.

    Returns
    -------
    pd.DataFrame
        Cleaned holdings ready for downstream use.
    """
    df = df.copy()

    # --- Tickers ---
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    # --- Dates ---
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    n_bad_dates = df["date"].isna().sum()
    if n_bad_dates:
        logger.warning(f"Dropped {n_bad_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])

    # --- Numeric columns ---
    for col in ["quantity", "avg_cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    n_bad_numeric = df[["quantity", "avg_cost"]].isna().any(axis=1).sum()
    if n_bad_numeric:
        logger.warning(f"Dropped {n_bad_numeric} rows with non-numeric quantity/avg_cost")
        df = df.dropna(subset=["quantity", "avg_cost"])

    # --- Defaults for optional fields ---
    df["asset_class"] = df.get("asset_class", pd.Series("Equity", index=df.index)).fillna("Equity")
    df["sector"] = df.get("sector", pd.Series("Unknown", index=df.index)).fillna("Unknown")
    df["region"] = df.get("region", pd.Series("US", index=df.index)).fillna("US")

    # --- Normalize unknown asset classes ---
    mask = ~df["asset_class"].isin(KNOWN_ASSET_CLASSES)
    if mask.any():
        logger.warning(
            f"Normalizing {mask.sum()} rows with unknown asset_class to 'Other': "
            f"{df.loc[mask, 'asset_class'].unique().tolist()}"
        )
        df.loc[mask, "asset_class"] = "Other"

    # --- Deduplication: keep last entry per (date, ticker) ---
    n_before = len(df)
    df = df.drop_duplicates(subset=["date", "ticker"], keep="last")
    if len(df) < n_before:
        logger.warning(f"Removed {n_before - len(df)} duplicate (date, ticker) rows")

    # --- Sort ---
    df = df.sort_values(["date", "ticker"]).reset_index(drop=True)

    logger.info(f"Holdings cleaned: {len(df)} rows, {df['ticker'].nunique()} tickers")
    return df
