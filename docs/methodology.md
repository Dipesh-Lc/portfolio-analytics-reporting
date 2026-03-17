# Methodology

## Return Conventions

- **Price data**: Adjusted close prices from Yahoo Finance (accounts for dividends and splits).
- **Daily return**: Simple arithmetic return — `r_t = (P_t / P_{t-1}) - 1`
- **Portfolio return**: Weighted sum of asset returns — `R_p = Σ w_i * r_i`
- **Weights**: Based on daily market values (`quantity × adj_close`), rebalanced daily under static holdings.
- **Cumulative return**: `(1 + r_1)(1 + r_2)...(1 + r_T) - 1`

## Annualization Assumptions

All annualized metrics assume **252 trading days per year**.

- Annualized return: `(1 + R_total)^(252/N) - 1`
- Annualized volatility: `σ_daily × √252`
- Sharpe ratio: `(r̄_excess_daily / σ_daily) × √252`

## Sharpe Ratio

`Sharpe = (R_p,ann - RF_ann) / σ_ann`

Risk-free rate sourced from Kenneth French's daily RF series (actual daily T-bill returns).

## Sortino Ratio

`Sortino = (R_p,ann - RF_ann) / DD_ann`

Where `DD_ann` = downside deviation (annualized standard deviation of returns below the risk-free rate).

## Max Drawdown

`MDD = min_t [ (NAV_t / max_{s≤t} NAV_s) - 1 ]`

Measures the worst peak-to-trough loss in the history.

## Value at Risk (VaR) — Historical Method

`VaR(c, h) = -Quantile(R, 1-c) × √h`

- Confidence level: 95% (configurable)
- Horizon: 1-day (scaled via square-root-of-time for multi-day)
- Method: Historical simulation — no distributional assumptions

**Why historical VaR**: Most transparent and directly testable method. Does not assume normality. Appropriate for portfolios with asymmetric return distributions.

## CVaR / Expected Shortfall

`CVaR(c) = -E[R | R ≤ VaR(c)]`

Average loss in the worst (1-c)% of scenarios. More conservative than VaR; captures tail severity.

## Fama-French 3-Factor Model

**Regression:**

`R_p,t - RF_t = α + β_mkt × (Mkt-RF)_t + β_smb × SMB_t + β_hml × HML_t + ε_t`

| Term | Meaning |
|------|---------|
| `β_mkt` | Market beta — systematic risk relative to market |
| `β_smb` | Size factor — positive = small-cap tilt |
| `β_hml` | Value factor — positive = value tilt, negative = growth tilt |
| `α` | Annual alpha — excess return beyond factor exposures |
| `R²` | Fraction of return variance explained by factors |

**Implementation details:**
- OLS estimation via `statsmodels`
- Heteroskedasticity-robust standard errors (HC3)
- Factor data from Kenneth French Data Library (daily series)
- All factor values in decimal form (not percent) before regression

## Reporting Assumptions

- Reports use prices as of the most recent available trading day.
- Holdings are treated as static (no intraday rebalancing modeled).
- No transaction costs, taxes, or borrowing costs included.
- Currency: USD only .

## Limitations

1. **Static holdings**: Does not track portfolio changes over time.
2. **No transaction costs**: All analytics are gross of fees and trading costs.
3. **Historical VaR only**: Does not account for forward-looking scenarios.
4. **US factors only**: Fama-French 3-factor model calibrated on U.S. equity market; international holdings (IEFA) attribution is approximate.
5. **Single currency**: No FX hedging or currency translation.


