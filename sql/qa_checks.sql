-- Data Quality Checks

-- 1. Check for price gaps > 5 trading days
SELECT ticker, date,
       LAG(date) OVER (PARTITION BY ticker ORDER BY date) AS prev_date,
       julianday(date) - julianday(LAG(date) OVER (PARTITION BY ticker ORDER BY date)) AS gap_days
FROM prices_daily
HAVING gap_days > 5
ORDER BY ticker, date;

-- 2. Tickers in holdings missing from prices
SELECT DISTINCT h.ticker
FROM holdings h
LEFT JOIN prices_daily p ON h.ticker = p.ticker
WHERE p.ticker IS NULL;

-- 3. Factor dates not in prices
SELECT f.date
FROM factors_daily f
LEFT JOIN portfolio_returns r ON f.date = r.date
WHERE r.date IS NULL
ORDER BY f.date;

-- 4. Impossible daily returns (> 50% in one day)
SELECT date, ticker, adj_close,
       LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) AS prev_close,
       (adj_close - LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date)) /
           LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) AS daily_ret
FROM prices_daily
HAVING ABS(daily_ret) > 0.5
ORDER BY ticker, date;

-- 5. Duplicate price records
SELECT date, ticker, COUNT(*) AS cnt
FROM prices_daily
GROUP BY date, ticker
HAVING cnt > 1;

-- 6. Stale holdings (not updated in 30+ days)
SELECT MAX(date) AS last_holdings_date,
       julianday('now') - julianday(MAX(date)) AS days_stale
FROM holdings
HAVING days_stale > 30;

-- 7. Negative quantities
SELECT * FROM holdings WHERE quantity <= 0;

-- 8. Missing factor dates (gaps > 5 trading days)
SELECT date,
       LAG(date) OVER (ORDER BY date) AS prev_date,
       julianday(date) - julianday(LAG(date) OVER (ORDER BY date)) AS gap_days
FROM factors_daily
HAVING gap_days > 5
ORDER BY date;
