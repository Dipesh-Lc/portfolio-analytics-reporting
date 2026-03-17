"""
Factor attribution: translates regression betas into business language.
Produces human-readable commentary on portfolio style and factor exposures.
"""

import pandas as pd

from src.analytics.factor_model import FactorModelResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


def interpret_factor_exposures(result: FactorModelResult) -> dict:
    """
    Translate factor regression results into business-language commentary.

    Returns
    -------
    dict with keys:
        - factor_loadings: dict of factor -> beta
        - commentary: list of human-readable strings
        - style_summary: one-line portfolio style description
        - attribution_table: DataFrame
    """
    betas = result.get_betas()
    commentary = []

    # Market beta interpretation
    b_mkt = result.beta_mkt
    if b_mkt > 1.1:
        commentary.append(
            f"The portfolio is aggressive relative to the market (beta={b_mkt:.2f}), "
            "amplifying both gains and losses."
        )
    elif b_mkt > 0.9:
        commentary.append(
            f"The portfolio has near-market exposure (beta={b_mkt:.2f}), "
            "closely tracking broad market moves."
        )
    elif b_mkt > 0.5:
        commentary.append(
            f"The portfolio is moderately defensive (beta={b_mkt:.2f}), "
            "with lower market sensitivity than the index."
        )
    else:
        commentary.append(
            f"The portfolio has low market exposure (beta={b_mkt:.2f}), "
            "suggesting significant non-market drivers of return."
        )

    # SMB (size) interpretation
    b_smb = result.beta_smb
    if b_smb > 0.3:
        commentary.append(
            f"A positive size loading (SMB={b_smb:.2f}) suggests a small-cap tilt, "
            "which historically carries a size risk premium but with higher volatility."
        )
    elif b_smb < -0.3:
        commentary.append(
            f"A negative size loading (SMB={b_smb:.2f}) confirms a large-cap bias, "
            "consistent with the Technology and ETF composition of the portfolio."
        )
    else:
        commentary.append(
            f"The size loading (SMB={b_smb:.2f}) is near zero, " "indicating no strong cap bias."
        )

    # HML (value) interpretation
    b_hml = result.beta_hml
    if b_hml > 0.3:
        commentary.append(
            f"A positive value loading (HML={b_hml:.2f}) indicates value orientation, "
            "favouring high book-to-market stocks."
        )
    elif b_hml < -0.3:
        commentary.append(
            f"A negative value loading (HML={b_hml:.2f}) confirms a growth tilt, "
            "consistent with Technology overweights."
        )
    else:
        commentary.append(
            f"The value loading (HML={b_hml:.2f}) is near neutral - "
            "the portfolio does not strongly favour either value or growth stocks."
        )

    # Alpha commentary
    alpha = result.alpha
    alpha_sig = result.alpha_pvalue < 0.10
    if alpha_sig and alpha > 0:
        commentary.append(
            f"The portfolio shows statistically significant positive alpha "
            f"({alpha:.2%}/yr, p={result.alpha_pvalue:.3f}), suggesting excess return "
            "beyond factor exposures - though interpret cautiously over short histories."
        )
    elif alpha_sig and alpha < 0:
        commentary.append(
            f"The portfolio shows negative alpha ({alpha:.2%}/yr, p={result.alpha_pvalue:.3f}), "
            "meaning it underperformed relative to its factor exposures."
        )
    else:
        commentary.append(
            f"Alpha is not statistically significant ({alpha:.2%}/yr, p={result.alpha_pvalue:.3f}). "
            "Returns are largely explained by factor exposures."
        )

    # R^2 commentary
    r2 = result.r_squared
    commentary.append(
        f"The 3-factor model explains {r2:.1%} of daily return variation (R^2={r2:.3f}). "
        + (
            "High explanatory power confirms factor-driven returns."
            if r2 > 0.85
            else "Some idiosyncratic return drivers are not captured by the three-factor model."
        )
    )

    # Build style summary
    size_label = "large-cap" if b_smb < -0.2 else "small-cap" if b_smb > 0.2 else "all-cap"
    style_label = "growth" if b_hml < -0.2 else "value" if b_hml > 0.2 else "blend"
    beta_label = "aggressive" if b_mkt > 1.1 else "defensive" if b_mkt < 0.8 else "market-like"
    style_summary = (
        f"{beta_label.capitalize()} {size_label} {style_label} portfolio "
        f"(beta={b_mkt:.2f}, alpha={alpha:.2%}/yr, R^2={r2:.0%})"
    )

    # Attribution table
    attribution_table = pd.DataFrame(
        {
            "Factor": list(betas.keys()) + ["Alpha (annual)"],
            "Loading": list(betas.values()) + [alpha],
            "P-value": [
                result.beta_mkt_pvalue,
                result.beta_smb_pvalue,
                result.beta_hml_pvalue,
                result.alpha_pvalue,
            ],
            "Significant (10%)": [
                p < 0.10
                for p in [
                    result.beta_mkt_pvalue,
                    result.beta_smb_pvalue,
                    result.beta_hml_pvalue,
                    result.alpha_pvalue,
                ]
            ],
        }
    )

    return {
        "factor_loadings": betas,
        "alpha_annual": alpha,
        "r_squared": r2,
        "commentary": commentary,
        "style_summary": style_summary,
        "attribution_table": attribution_table,
    }
