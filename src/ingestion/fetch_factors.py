"""
Fama-French factor data ingestion.
Downloads daily factor returns from Kenneth French's Data Library.
"""

import io
import zipfile
from typing import Optional

import pandas as pd
import requests

from src.utils.logger import get_logger
from src.utils.paths import RAW_DIR

logger = get_logger(__name__)

FF_DAILY_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)


def fetch_factors(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    save_raw: bool = True,
) -> pd.DataFrame:
    """
    Download and parse daily Fama-French 3-factor data.

    Factors:
        Mkt-RF : Market excess return (market premium)
        SMB    : Small Minus Big (size factor)
        HML    : High Minus Low (value factor)
        RF     : Risk-free rate

    All values are in DECIMAL form after this function (not percent).

    Parameters
    ----------
    start_date : str, optional
        Filter start date (YYYY-MM-DD).
    end_date : str, optional
        Filter end date (YYYY-MM-DD).
    save_raw : bool
        Whether to save parsed CSV to data/raw/.

    Returns
    -------
    pd.DataFrame
        Columns: date, mkt_rf, smb, hml, rf  (all decimal)
    """
    logger.info("Fetching Fama-French daily factors from Kenneth French Data Library")

    try:
        response = requests.get(FF_DAILY_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to download FF factors: {e}")
        raise

    # Unzip in memory
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
        with zf.open(csv_name) as f:
            raw_text = f.read().decode("utf-8", errors="replace")

    df = _parse_ff_csv(raw_text)

    # Convert from percent to decimal
    for col in ["mkt_rf", "smb", "hml", "rf"]:
        if col in df.columns:
            df[col] = df[col] / 100.0

    # Date filters
    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    if save_raw:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RAW_DIR / "factors_ff_daily.parquet"
        df.to_parquet(out_path, index=False)
        logger.info(f"Raw factors saved to {out_path}")

    logger.info(
        f"Loaded {len(df)} factor rows from {df['date'].min().date()} to {df['date'].max().date()}"
    )
    return df


def _parse_ff_csv(raw_text: str) -> pd.DataFrame:
    """
    Parse the Kenneth French CSV format.
    The file has a header section before the data starts.
    Data rows look like: 19260701,-0.32,-0.24,-0.52,0.009
    """
    lines = raw_text.splitlines()
    data_lines = []
    in_data = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Data rows start with 8-digit date
        parts = stripped.split(",")
        if len(parts) >= 5 and parts[0].strip().isdigit() and len(parts[0].strip()) == 8:
            in_data = True
            data_lines.append(stripped)
        elif in_data and len(parts) >= 5 and parts[0].strip().isdigit():
            data_lines.append(stripped)

    if not data_lines:
        raise ValueError("Could not parse factor data - format may have changed.")

    records = []
    for line in data_lines:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            date_str = parts[0]
            row = {
                "date": pd.to_datetime(date_str, format="%Y%m%d"),
                "mkt_rf": float(parts[1]),
                "smb": float(parts[2]),
                "hml": float(parts[3]),
                "rf": float(parts[4]),
            }
            records.append(row)
        except (ValueError, IndexError):
            continue

    df = pd.DataFrame(records)
    df = df.sort_values("date").reset_index(drop=True)
    return df
