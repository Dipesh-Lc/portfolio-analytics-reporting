"""Tests for holdings and factor ingestion."""

import textwrap
from pathlib import Path

import pandas as pd
import pytest

from src.ingestion.load_holdings import get_holdings_date, get_tickers, load_holdings

SAMPLE_CSV = textwrap.dedent("""\
    date,ticker,quantity,avg_cost,asset_class,sector,region
    2024-01-02,AAPL,50,185.20,Equity,Technology,US
    2024-01-02,MSFT,35,372.40,Equity,Technology,US
    2024-01-02,SPY,20,470.00,ETF,Index,US
""")


@pytest.fixture
def sample_holdings_file(tmp_path):
    f = tmp_path / "holdings.csv"
    f.write_text(SAMPLE_CSV)
    return f


def test_load_holdings_returns_dataframe(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_load_holdings_required_columns(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    for col in ["date", "ticker", "quantity", "avg_cost"]:
        assert col in df.columns


def test_load_holdings_tickers_uppercase(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    for t in df["ticker"]:
        assert t == t.upper()


def test_load_holdings_date_is_datetime(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_load_holdings_missing_required_column(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("date,ticker\n2024-01-02,AAPL\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_holdings(f)


def test_load_holdings_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_holdings(Path("/nonexistent/file.csv"))


def test_get_tickers(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    tickers = get_tickers(df)
    assert set(tickers) == {"AAPL", "MSFT", "SPY"}
    assert tickers == sorted(tickers)  # Should be sorted


def test_get_holdings_date(sample_holdings_file):
    df = load_holdings(sample_holdings_file)
    d = get_holdings_date(df)
    assert d == pd.Timestamp("2024-01-02")
