# Stakeholder Notes

## Who This Is For

| Audience | What They Care About |
|----------|---------------------|
| Portfolio Managers | Cumulative return, Sharpe ratio, factor tilts, alpha |
| Risk Officers | VaR, CVaR, max drawdown, rolling volatility, concentration |
| Operations | Data freshness, report availability, holdings accuracy |
| Senior Management | One-page summary: P&L, style, risk budget utilization |

## Report Sections and Their Purpose

### Performance Summary
Shows how the portfolio has performed over the analysis period. The equity curve and monthly heatmap are the primary views for portfolio managers.

**Key questions answered:**
- How much has the portfolio made?
- Is the risk-adjusted return (Sharpe) competitive?
- Which months were strong / weak?

### Risk Analytics
Quantifies downside risk. VaR and CVaR are the primary metrics for risk budget discussions.

**Key questions answered:**
- What is the worst expected 1-day loss at 95% confidence?
- How deep was the worst drawdown?
- Is volatility within expected range?

### Factor Attribution
Explains *why* the portfolio performed the way it did using systematic risk factors.

**Key questions answered:**
- How much of the return is explained by market beta?
- Does the portfolio have unintended style tilts (size/value)?
- Is there any alpha beyond factor compensation?

## Reporting Cadence

| Frequency | Trigger | Audience |
|-----------|---------|----------|
| Weekly (Monday 8am) | `scheduled_report.py` | Portfolio Managers, Risk |
| Ad-hoc | `make pipeline` | Analysts |
| On demand | Streamlit dashboard | Any stakeholder |

## How to Interpret the Factor Model

The Fama-French 3-factor model is the industry standard for attributing equity portfolio returns. A simplified guide:

- **Market beta near 1.0**: Normal market exposure — portfolio rises/falls with the market.
- **Market beta > 1.2**: Aggressive — amplifies market moves. Higher risk/return.
- **Market beta < 0.8**: Defensive — dampens market moves. Lower risk, useful in downturns.
- **SMB > 0.3**: Meaningful small-cap tilt. Historically rewarded but with higher volatility.
- **HML < -0.3**: Growth bias. Consistent with Technology and momentum positions.
- **Alpha > 0 and p < 0.10**: Evidence of manager skill (or good luck). Interpret cautiously with short histories.
- **R² > 0.85**: Returns are primarily factor-driven. Limited idiosyncratic exposure.

## Important Caveats

1. **This is not investment advice.** The platform is an internal risk monitoring tool.
2. **Past performance**: All analytics are backward-looking. Factor exposures may change with rebalancing.
4. **VaR limitations**: Historical VaR assumes the future resembles the past. Tail events outside the historical window are not captured.
5. **Static holdings**: The platform does not track intraday position changes. Holdings are snapshot-based.

