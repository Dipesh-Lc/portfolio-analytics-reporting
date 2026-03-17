-- Analytics Views

-- Latest portfolio weights by ticker
CREATE VIEW IF NOT EXISTS v_latest_weights AS
SELECT
    h.ticker,
    h.quantity,
    h.avg_cost,
    h.asset_class,
    h.sector,
    h.region,
    p.adj_close AS current_price,
    h.quantity * p.adj_close AS market_value,
    h.quantity * h.avg_cost AS cost_basis,
    (h.quantity * p.adj_close - h.quantity * h.avg_cost) AS unrealized_pnl
FROM holdings h
JOIN prices_daily p ON h.ticker = p.ticker
WHERE p.date = (SELECT MAX(date) FROM prices_daily WHERE ticker = h.ticker)
  AND h.date = (SELECT MAX(date) FROM holdings);

-- Rolling 30-day return stats
CREATE VIEW IF NOT EXISTS v_rolling_30d AS
SELECT
    date,
    daily_return,
    AVG(daily_return) OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_mean_30d,
    cumulative_return,
    portfolio_value
FROM portfolio_returns
ORDER BY date;
