"""
Yahoo Finance price ingestion module.
Fetches adjusted daily prices, dividends, and splits for portfolio tickers.
"""

from datetime import date
from typing import Optional

import pandas as pd
import yfinance as yf

from src.utils.logger import get_logger
from src.utils.paths import RAW_DIR

logger = get_logger(__name__)


def fetch_prices(
    tickers: list[str],
    start_date: str,
    end_date: Optional[str] = None,
    save_raw: bool = True,
) -> pd.DataFrame:
    """
    Fetch adjusted daily closing prices from Yahoo Finance.

    Parameters
    ----------
    tickers : list[str]
        List of ticker symbols.
    start_date : str
        Start date in YYYY-MM-DD format.
    end_date : str, optional
        End date. Defaults to today.
    save_raw : bool
        Whether to save raw data to data/raw/.

    Returns
    -------
    pd.DataFrame
        Long-format DataFrame with columns: date, ticker, open, high, low,
        close, adj_close, volume, dividends, stock_splits.
    """
    end_date = end_date or date.today().isoformat()
    logger.info(f"Fetching prices for {len(tickers)} tickers: {tickers}")
    logger.info(f"Date range: {start_date} to {end_date}")

    all_frames = []
    failed = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            hist = t.history(start=start_date, end=end_date, auto_adjust=False)

            if hist.empty:
                logger.warning(f"No price data returned for {ticker}")
                failed.append(ticker)
                continue

            hist = hist.reset_index()
            hist.columns = [c.lower().replace(" ", "_") for c in hist.columns]

            # Normalize column names
            rename_map = {
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "adj_close": "adj_close",
                "volume": "volume",
                "dividends": "dividends",
                "stock_splits": "stock_splits",
            }
            hist = hist.rename(columns=rename_map)

            # Keep only known columns
            keep_cols = [c for c in rename_map.values() if c in hist.columns]
            hist = hist[keep_cols].copy()

            # Ensure date is date only (strip time)
            hist["date"] = pd.to_datetime(hist["date"]).dt.normalize()

            # Remove timezone info if present
            if hasattr(hist["date"].dtype, "tz") and hist["date"].dt.tz is not None:
                hist["date"] = hist["date"].dt.tz_localize(None)

            hist["ticker"] = ticker
            hist = hist.dropna(subset=["adj_close"])

            all_frames.append(hist)
            logger.debug(
                f"{ticker}: {len(hist)} rows from {hist['date'].min().date()} to {hist['date'].max().date()}"
            )

        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            failed.append(ticker)

    if not all_frames:
        raise RuntimeError("No price data fetched for any ticker.")

    if failed:
        logger.warning(f"Failed tickers: {failed}")

    prices = pd.concat(all_frames, ignore_index=True)
    prices = prices.sort_values(["date", "ticker"]).reset_index(drop=True)

    if save_raw:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RAW_DIR / "prices_raw.parquet"
        prices.to_parquet(out_path, index=False)
        logger.info(f"Raw prices saved to {out_path}")

    logger.info(f"Fetched {len(prices)} price rows for {prices['ticker'].nunique()} tickers")
    return prices


def get_adj_close_panel(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot prices to a wide adj_close panel: rows=dates, columns=tickers.
    """
    panel = prices.pivot(index="date", columns="ticker", values="adj_close")
    panel = panel.sort_index()
    return panel
