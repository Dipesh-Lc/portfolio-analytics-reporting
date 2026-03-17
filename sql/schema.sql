-- Portfolio Analytics Database Schema
-- SQLite compatible

-- Holdings: position file as ingested
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    ticker TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    asset_class TEXT,
    sector TEXT,
    region TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, ticker)
);

-- Daily prices for all tickers
CREATE TABLE IF NOT EXISTS prices_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    ticker TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adj_close REAL NOT NULL,
    volume REAL,
    dividends REAL DEFAULT 0,
    stock_splits REAL DEFAULT 0,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, ticker)
);

-- Fama-French factor data (daily)
CREATE TABLE IF NOT EXISTS factors_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    mkt_rf REAL NOT NULL,  -- Market excess return
    smb REAL NOT NULL,     -- Small minus Big
    hml REAL NOT NULL,     -- High minus Low (value)
    rf REAL NOT NULL,      -- Risk-free rate
    mom REAL,              -- Momentum (optional, from MOM file)
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Portfolio returns (daily)
CREATE TABLE IF NOT EXISTS portfolio_returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    daily_return REAL NOT NULL,
    cumulative_return REAL NOT NULL,
    daily_pnl REAL,
    cumulative_pnl REAL,
    portfolio_value REAL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Snapshot of computed analytics per run
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date DATE NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    period_start DATE,
    period_end DATE,
    notes TEXT,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices_daily(ticker);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices_daily(date);
CREATE INDEX IF NOT EXISTS idx_factors_date ON factors_daily(date);
CREATE INDEX IF NOT EXISTS idx_returns_date ON portfolio_returns(date);
