# System Architecture

## High-Level Flow

```
Holdings CSV (data/samples/)
         │
         ▼
┌────────────────────┐     ┌──────────────────────┐
│   load_holdings    │     │    fetch_prices       │
│   (ingestion/)     │     │  (Yahoo Finance via   │
└────────┬───────────┘     │    yfinance)          │
         │                 └──────────┬───────────┘
         │                            │
         │              ┌─────────────▼──────────┐
         │              │     fetch_factors       │
         │              │  (Kenneth French Lib)   │
         │              └─────────────┬──────────┘
         │                            │
         ▼                            ▼
┌────────────────────────────────────────────────┐
│               data_checks (validation/)         │
│  - holdings QA   - price gaps   - factor units  │
└──────────────────────────┬─────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────┐
│              SQLite Warehouse                     │
│  holdings | prices_daily | factors_daily |        │
│  portfolio_returns | analytics_snapshots          │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────┐
│             Processing Layer                      │
│  build_prices_panel → asset_returns               │
│  positions → weights → portfolio_returns + PnL    │
└──────────────────────────┬───────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────┐
│             Analytics Engine                      │
│  performance.py  │  risk.py  │  factor_model.py   │
│  attribution.py  │           │                    │
└──────────────────────────┬───────────────────────┘
                           │
            ┌──────────────┴───────────────┐
            ▼                              ▼
┌───────────────────┐           ┌──────────────────────┐
│  charts.py        │           │  generate_report.py  │
│  (artifacts/      │           │  (artifacts/reports/ │
│   figures/)       │           │   report_YYYY-MM-DD  │
└───────────────────┘           │   .html)             │
                                └──────────────────────┘
                                          │
                                          ▼
                                ┌──────────────────────┐
                                │  Streamlit Dashboard  │
                                │  src/app/Home.py      │
                                │  pages/01_Summary     │
                                │  pages/02_Risk        │
                                │  pages/03_Factor      │
                                └──────────────────────┘
```

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `ingestion/` | Read raw data from external sources. No business logic. |
| `validation/` | Assert data contracts. Raise warnings/errors. |
| `processing/` | Transform raw data into analytics-ready structures. |
| `warehouse/` | Persist data and analytics to SQLite. |
| `analytics/` | Compute all metrics. Pure functions — no I/O. |
| `reporting/` | Render outputs as HTML report and charts. |
| `app/` | Interactive Streamlit dashboard. |
| `pipelines/` | Orchestrate end-to-end workflow. |
| `utils/` | Shared logger and path constants. |

## Data Flow: Key Objects

| Object | Type | Description |
|--------|------|-------------|
| `holdings` | `pd.DataFrame` | ticker, quantity, avg_cost, metadata |
| `prices` | `pd.DataFrame` | Long-format: date × ticker × adj_close |
| `panel` | `pd.DataFrame` | Wide: dates × tickers, adj_close values |
| `asset_returns` | `pd.DataFrame` | Wide: dates × tickers, daily returns |
| `weights` | `pd.DataFrame` | Wide: dates × tickers, daily portfolio weights |
| `port_returns` | `pd.Series` | Daily portfolio return series |
| `factors` | `pd.DataFrame` | date, mkt_rf, smb, hml, rf (decimal) |
| `FactorModelResult` | dataclass | All regression outputs + diagnostics |

