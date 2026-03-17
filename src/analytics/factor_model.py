"""
Fama-French factor model regression.
Estimates portfolio factor exposures (betas) using OLS.

Model:
    R_p - RF = alpha + beta_mkt*(Mkt-RF) + beta_smb*SMB + beta_hml*HML + epsilon

This decomposes portfolio excess returns into:
    - Market risk exposure (beta_mkt)
    - Size tilt (beta_smb): positive = small-cap bias
    - Value tilt (beta_hml): positive = value bias, negative = growth bias
    - Alpha: return unexplained by factors
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FactorModelResult:
    """Results from Fama-French factor regression."""

    alpha: float
    alpha_pvalue: float
    beta_mkt: float
    beta_mkt_pvalue: float
    beta_smb: float
    beta_smb_pvalue: float
    beta_hml: float
    beta_hml_pvalue: float
    r_squared: float
    adj_r_squared: float
    n_obs: int
    residual_std: float
    info_ratio: float  # alpha / residual_std (annualized)
    regression_summary: str

    def to_dict(self) -> dict:
        return {
            "alpha": self.alpha,
            "alpha_pvalue": self.alpha_pvalue,
            "beta_mkt": self.beta_mkt,
            "beta_mkt_pvalue": self.beta_mkt_pvalue,
            "beta_smb": self.beta_smb,
            "beta_smb_pvalue": self.beta_smb_pvalue,
            "beta_hml": self.beta_hml,
            "beta_hml_pvalue": self.beta_hml_pvalue,
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "n_obs": self.n_obs,
            "residual_std": self.residual_std,
            "info_ratio": self.info_ratio,
        }

    def get_betas(self) -> dict[str, float]:
        return {
            "Market (Mkt-RF)": self.beta_mkt,
            "Size (SMB)": self.beta_smb,
            "Value (HML)": self.beta_hml,
        }


def run_factor_regression(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    trading_days: int = 252,
) -> FactorModelResult:
    """
    Run OLS Fama-French 3-factor regression.

    Parameters
    ----------
    portfolio_returns : pd.Series
        Daily portfolio total returns (not excess).
    factors : pd.DataFrame
        Daily factor data with columns: date, mkt_rf, smb, hml, rf.
        All values should be in decimal form.
    trading_days : int
        For annualizing alpha.

    Returns
    -------
    FactorModelResult
    """
    # Align dates
    factors_indexed = factors.set_index("date") if "date" in factors.columns else factors
    factors_indexed.index = pd.to_datetime(factors_indexed.index).normalize()
    port_indexed = portfolio_returns.copy()
    port_indexed.index = pd.to_datetime(port_indexed.index).normalize()

    common_dates = port_indexed.index.intersection(factors_indexed.index)
    if len(common_dates) < 30:
        raise ValueError(
            f"Too few overlapping dates for regression: {len(common_dates)}. "
            "Check that factor and price date ranges overlap."
        )

    port_aligned = port_indexed.loc[common_dates]
    factors_aligned = factors_indexed.loc[common_dates]

    # Compute excess returns: R_p - RF
    excess_returns = port_aligned - factors_aligned["rf"]

    # Factor exposures
    X = factors_aligned[["mkt_rf", "smb", "hml"]]
    X = sm.add_constant(X)
    y = excess_returns

    # Drop any rows with NaN
    valid = X.notna().all(axis=1) & y.notna()
    X = X[valid]
    y = y[valid]

    model = sm.OLS(y, X).fit(cov_type="HC3")  # Heteroskedasticity-robust SEs

    alpha_daily = float(model.params["const"])
    alpha_annual = float((1 + alpha_daily) ** trading_days - 1)
    residual_std = float(model.resid.std() * np.sqrt(trading_days))
    info_ratio = float(alpha_annual / residual_std) if residual_std > 0 else np.nan

    result = FactorModelResult(
        alpha=alpha_annual,
        alpha_pvalue=float(model.pvalues["const"]),
        beta_mkt=float(model.params["mkt_rf"]),
        beta_mkt_pvalue=float(model.pvalues["mkt_rf"]),
        beta_smb=float(model.params["smb"]),
        beta_smb_pvalue=float(model.pvalues["smb"]),
        beta_hml=float(model.params["hml"]),
        beta_hml_pvalue=float(model.pvalues["hml"]),
        r_squared=float(model.rsquared),
        adj_r_squared=float(model.rsquared_adj),
        n_obs=int(model.nobs),
        residual_std=residual_std,
        info_ratio=info_ratio,
        regression_summary=model.summary().as_text(),
    )

    logger.info(
        f"Factor model: alpha={alpha_annual:.2%}/yr, beta_mkt={result.beta_mkt:.3f}, "
        f"SMB={result.beta_smb:.3f}, HML={result.beta_hml:.3f}, R^2={result.r_squared:.3f}"
    )
    return result
