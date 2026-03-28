# Portfolio Analytics & Reporting Platform

![Python](https://img.shields.io/badge/python-3.11-blue)
![Streamlit](https://img.shields.io/badge/dashboard-streamlit-red)
![License](https://img.shields.io/badge/license-MIT-green)

---

> An automated internal portfolio analytics system that ingests holdings and market data, computes performance and risk metrics (Sharpe ratio, drawdown, VaR), estimates factor exposures using Fama-French regressions, and generates recurring stakeholder-ready reports and dashboards.

---

## Business Problem

Portfolio managers and risk teams need a reliable, automated way to monitor portfolio performance, quantify risk, and understand factor exposures without manually running spreadsheets or ad-hoc scripts. This platform simulates a real internal analytics product used by investment teams.

**Users:** Portfolio managers, risk analysts, operations teams  
**Reporting cadence:** Daily or weekly automated reports  
**Business value:** Reduces manual reporting effort, standardizes risk metrics, enables proactive risk monitoring

---

## System Architecture

```
Holdings CSV
     ↓
Price + Factor Ingestion (Yahoo Finance + Kenneth French)
     ↓
Validation + Normalization
     ↓
SQLite Warehouse (holdings, prices, factors, returns)
     ↓
Analytics Engine
     ↓
Performance / Risk / Attribution Outputs
     ↓
Automated HTML Report + Streamlit Dashboard
```

---

## Metrics Computed

| Category       | Metrics |
|----------------|---------|
| Performance    | Cumulative return, annualized return, Sharpe ratio, Sortino ratio, hit ratio |
| Risk           | Volatility, max drawdown, rolling drawdown, historical VaR (95%), CVaR/ES |
| Attribution    | Market beta, SMB, HML factor loadings, R², alpha |
| Concentration  | Sector weights, position weights, top-N exposure |

---

## Data Sources

- **Holdings:** `data/samples/portfolio_holdings.csv` -- simulated internal position file
- **Prices:** Yahoo Finance via `yfinance` -- adjusted daily closes, dividends, splits
- **Factors:** Kenneth French Data Library -- daily Fama-French 3-factor series 

Factors used:

-   **Mkt-RF** --- Market risk premium
-   **SMB** --- Size factor (small minus big)
-   **HML** --- Value factor (high minus low)

---

## Quick Start

```bash
# 1. Create and activate environment
conda env create -f environment.yml
conda activate portfolio-analytics-reporting

# 2. Copy env config
cp .env.example .env

# 3. Run the full pipeline
python -m src.pipelines.run_pipeline

# 4. Launch the Streamlit dashboard
streamlit run src/app/Home.py

# 5. Run tests
pytest tests/
```

---

## Project Structure

```
src/
├── ingestion/      # Load holdings, fetch prices + factors
├── validation/     # Data quality checks
├── processing/     # Clean data, build panels, compute returns
├── warehouse/      # SQLite DB layer
├── analytics/      # Performance, risk, factor model
├── reporting/      # Charts, HTML report generation
├── app/            # Streamlit multipage dashboard
└── pipelines/      # Orchestration + scheduling
```

---

## Technology Stack

-  Language:          Python 3.11
-  Data Processing:   Pandas, NumPy
-  Statistics:        Statsmodels
-  Visualization:     Plotly, Matplotlib
-  Dashboard:         Streamlit
-  Storage:           SQLite + SQLAlchemy
-  Testing:           PyTest
-  Configuration:     YAML
-  Data Sources:      Yahoo Finance, Fama-French

---

## Screenshots

Run the pipeline to generate charts in `artifacts/figures/` and an HTML report in `artifacts/reports/`.

---

## Limitations

-   Single currency (USD)
-   Static holdings (no trade history)
-   Historical VaR only
-   No transaction cost modeling
-   U.S. Fama-French factors only

## Possible Future Improvements 

-   Rolling factor exposures
-   Benchmark comparison (SPY)
-   Monte-Carlo VaR
-   Expected shortfall forecasting
-   Email / Slack report delivery
-   International factor models

