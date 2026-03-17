"""
Data quality validation layer.
Prevents bad operational data from contaminating analytics.
"""

from dataclasses import dataclass, field

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)

VALID_ASSET_CLASSES = {"Equity", "ETF", "Bond", "Commodity", "Cash", "Other"}


@dataclass
class ValidationResult:
    """Collects all validation issues found during data checks."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)
        logger.error(f"[VALIDATION ERROR] {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        logger.warning(f"[VALIDATION WARNING] {msg}")

    def summary(self) -> str:
        lines = [f"Validation: {'PASSED' if self.is_valid else 'FAILED'}"]
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"    - {e}")
        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


def validate_holdings(df: pd.DataFrame) -> ValidationResult:
    """Run all data quality checks on holdings DataFrame."""
    result = ValidationResult()

    # Missing tickers
    null_tickers = df["ticker"].isna().sum()
    if null_tickers > 0:
        result.add_error(f"{null_tickers} rows have missing ticker")

    # Negative quantities
    neg_qty = df[df["quantity"] <= 0]
    if len(neg_qty) > 0:
        result.add_error(
            f"{len(neg_qty)} rows have non-positive quantity: {neg_qty['ticker'].tolist()}"
        )

    # Negative average cost
    neg_cost = df[df["avg_cost"] <= 0]
    if len(neg_cost) > 0:
        result.add_error(
            f"{len(neg_cost)} rows have non-positive avg_cost: {neg_cost['ticker'].tolist()}"
        )

    # Duplicate ticker rows
    dupes = df.duplicated(subset=["date", "ticker"], keep=False)
    if dupes.any():
        result.add_error(f"Duplicate (date, ticker) rows: {df[dupes]['ticker'].tolist()}")

    # Invalid dates
    if df["date"].isna().any():
        result.add_error("Some rows have invalid/null dates")

    # Invalid asset classes
    if "asset_class" in df.columns:
        invalid = df[~df["asset_class"].isin(VALID_ASSET_CLASSES)]
        if len(invalid) > 0:
            result.add_warning(
                f"Unknown asset_class values: {invalid['asset_class'].unique().tolist()}"
            )

    logger.info(result.summary())
    return result


def validate_prices(prices: pd.DataFrame, tickers: list[str]) -> ValidationResult:
    """Run data quality checks on price data."""
    result = ValidationResult()

    # Check all requested tickers are present
    present = set(prices["ticker"].unique())
    missing = set(tickers) - present
    if missing:
        result.add_warning(f"Missing price data for tickers: {sorted(missing)}")

    # Check for excessive NaN in adj_close
    for ticker, group in prices.groupby("ticker"):
        nan_pct = group["adj_close"].isna().mean()
        if nan_pct > 0.05:
            result.add_warning(f"{ticker}: {nan_pct:.1%} NaN adj_close values")

    # Check for impossible single-day returns (> 50%)
    prices_sorted = prices.sort_values(["ticker", "date"])
    prices_sorted["prev_close"] = prices_sorted.groupby("ticker")["adj_close"].shift(1)
    prices_sorted["daily_ret"] = prices_sorted["adj_close"] / prices_sorted["prev_close"] - 1
    extreme = prices_sorted[prices_sorted["daily_ret"].abs() > 0.5]
    if len(extreme) > 0:
        result.add_warning(
            f"{len(extreme)} extreme daily returns (>50%) found - check for splits/errors: "
            f"{extreme[['ticker','date','daily_ret']].to_dict('records')[:3]}"
        )

    # Price gaps > 5 business days per ticker
    for ticker, group in prices.groupby("ticker"):
        dates = pd.to_datetime(group["date"]).sort_values()
        gaps = dates.diff().dt.days
        max_gap = gaps.max()
        if max_gap and max_gap > 7:
            result.add_warning(f"{ticker}: max gap of {max_gap} calendar days in price series")

    logger.info(result.summary())
    return result


def validate_factors(factors: pd.DataFrame, prices: pd.DataFrame) -> ValidationResult:
    """Check factor data alignment and sanity."""
    result = ValidationResult()

    if factors.empty:
        result.add_error("Factor dataset is empty")
        return result

    # Check unit: factors should be decimals (~-0.1 to 0.1 daily)
    for col in ["mkt_rf", "smb", "hml", "rf"]:
        if col in factors.columns:
            max_val = factors[col].abs().max()
            if max_val > 0.5:
                result.add_error(
                    f"Factor '{col}' appears to be in percent, not decimal (max={max_val:.4f}). "
                    "Divide by 100 before use."
                )

    # Check date alignment with price data
    price_dates = set(pd.to_datetime(prices["date"]).dt.normalize().unique())
    factor_dates = set(pd.to_datetime(factors["date"]).dt.normalize().unique())
    overlap = price_dates & factor_dates
    if len(overlap) < 10:
        result.add_error(f"Very low date overlap between factors and prices: {len(overlap)} days")

    logger.info(result.summary())
    return result
