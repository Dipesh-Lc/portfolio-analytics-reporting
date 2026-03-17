"""
Streamlit Page: Factor Attribution
Fama-French 3-factor regression results, betas, alpha, and commentary.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

st.set_page_config(page_title="Factor Attribution", page_icon="🔬", layout="wide")
st.title("🔬 Factor Attribution — Fama-French 3-Factor Model")

st.markdown("""
    Estimates portfolio factor exposures using OLS regression:

    **R_p - RF = α + β_mkt·(Mkt-RF) + β_smb·SMB + β_hml·HML + ε**

    - **Mkt-RF** — Market risk premium (excess return of market over risk-free)
    - **SMB** — Small Minus Big (size factor: positive = small-cap tilt)
    - **HML** — High Minus Low (value factor: positive = value, negative = growth)
    - **α** — Abnormal return unexplained by the three factors
    """)


@st.cache_data(ttl=3600, show_spinner="Running factor regression...")
def get_outputs():
    from src.pipelines.run_pipeline import run_pipeline

    return run_pipeline()


try:
    if "pipeline_outputs" not in st.session_state:
        st.warning("Run the pipeline from the Home page first.")
        st.stop()
    out = st.session_state["pipeline_outputs"]

except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

factor_result = out.get("factor_result")
attribution = out.get("attribution", {})

if factor_result is None:
    st.warning("Factor regression unavailable. Check that factor data downloaded successfully.")
    st.stop()

# ------------------------------------------------------------------ #
# Style summary
# ------------------------------------------------------------------ #
st.info(f"**Portfolio Style:** {attribution.get('style_summary', 'N/A')}")

# ------------------------------------------------------------------ #
# Factor loading cards
# ------------------------------------------------------------------ #
st.subheader("Factor Loadings")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Market Beta (β)",
    f"{factor_result.beta_mkt:.3f}",
    help="Sensitivity to market moves. >1 = aggressive, <1 = defensive.",
)
c2.metric(
    "Size (SMB)",
    f"{factor_result.beta_smb:.3f}",
    help="Positive = small-cap tilt. Negative = large-cap tilt.",
)
c3.metric(
    "Value (HML)", f"{factor_result.beta_hml:.3f}", help="Positive = value. Negative = growth."
)
c4.metric(
    "Annual Alpha",
    f"{factor_result.alpha:.2%}",
    delta=f"p={factor_result.alpha_pvalue:.3f}",
    help="Excess return beyond factor exposures (annualized).",
)
c5.metric(
    "R² (Explained)",
    f"{factor_result.r_squared:.1%}",
    help="Fraction of return variance explained by the 3-factor model.",
)

# ------------------------------------------------------------------ #
# Factor loadings bar chart
# ------------------------------------------------------------------ #
st.subheader("Factor Exposure Chart")
betas = {
    "Market (Mkt-RF)": factor_result.beta_mkt,
    "Size (SMB)": factor_result.beta_smb,
    "Value (HML)": factor_result.beta_hml,
}
colors = ["#2563EB" if v >= 0 else "#DC2626" for v in betas.values()]

fig = go.Figure(
    go.Bar(
        x=list(betas.keys()),
        y=list(betas.values()),
        marker_color=colors,
        text=[f"{v:.3f}" for v in betas.values()],
        textposition="outside",
        width=0.5,
    )
)
fig.add_hline(y=0, line_color="#374151", line_width=1)
fig.update_layout(
    height=350,
    template="plotly_white",
    yaxis_title="Factor Beta",
    xaxis_title="",
    title=f"Fama-French Factor Betas  |  R² = {factor_result.r_squared:.1%}  |  N = {factor_result.n_obs}",
    margin=dict(l=0, r=0, t=50, b=0),
)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ #
# Regression table
# ------------------------------------------------------------------ #
st.subheader("Regression Results")
attr_table = attribution.get("attribution_table")
if attr_table is not None and len(attr_table) > 0:

    def highlight_sig(row):
        if row.get("Significant (10%)", False):
            return ["font-weight: bold"] * len(row)
        return [""] * len(row)

    styled = attr_table.style.apply(highlight_sig, axis=1).format(
        {
            "Loading": "{:.4f}",
            "P-value": "{:.4f}",
        }
    )
    st.dataframe(styled, use_container_width=True)
    st.caption("Bold rows = statistically significant at 10% level. HC3 robust standard errors.")

# ------------------------------------------------------------------ #
# Commentary
# ------------------------------------------------------------------ #
st.subheader("Interpretation")
for comment in attribution.get("commentary", []):
    st.info(comment)

# ------------------------------------------------------------------ #
# Full regression output (expander)
# ------------------------------------------------------------------ #
with st.expander("📋 Full OLS Regression Output (statsmodels)"):
    st.code(factor_result.regression_summary, language=None)

# ------------------------------------------------------------------ #
# Explained vs unexplained return (pie)
# ------------------------------------------------------------------ #
st.subheader("Return Variance Decomposition")
col_pie, col_meta = st.columns([1, 2])
with col_pie:
    r2 = factor_result.r_squared
    fig_pie = go.Figure(
        go.Pie(
            labels=["Explained by factors", "Unexplained (idiosyncratic)"],
            values=[r2 * 100, (1 - r2) * 100],
            hole=0.5,
            marker_colors=["#2563EB", "#E5E7EB"],
            textinfo="label+percent",
        )
    )
    fig_pie.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

with col_meta:
    st.markdown("**Model diagnostics**")
    diag = {
        "N observations": factor_result.n_obs,
        "R²": f"{factor_result.r_squared:.4f}",
        "Adj. R²": f"{factor_result.adj_r_squared:.4f}",
        "Residual std (annual)": f"{factor_result.residual_std:.2%}",
        "Info ratio (α/σ_ε)": (
            f"{factor_result.info_ratio:.2f}"
            if factor_result.info_ratio == factor_result.info_ratio
            else "N/A"
        ),
        "Alpha (annual)": f"{factor_result.alpha:.2%}",
        "Alpha p-value": f"{factor_result.alpha_pvalue:.4f}",
    }
    diag_df = pd.DataFrame(list(diag.items()), columns=["Metric", "Value"])
    diag_df["Value"] = diag_df["Value"].astype(str)

    st.dataframe(diag_df, width="stretch", hide_index=True)
