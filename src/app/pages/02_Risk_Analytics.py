"""
Streamlit Page: Risk Analytics
Shows drawdown, VaR, rolling volatility, return distribution, and concentration.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

st.set_page_config(page_title="Risk Analytics", page_icon="⚠️", layout="wide")
st.title("⚠️ Risk Analytics")


@st.cache_data(ttl=3600, show_spinner="Loading risk data...")
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

port_returns = out["portfolio_returns"]
risk = out["risk_metrics"]

# ------------------------------------------------------------------ #
# Risk metric cards
# ------------------------------------------------------------------ #
st.subheader("Risk Summary")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Max Drawdown", f"{risk.get('max_drawdown', 0):.2%}")
c2.metric("Ann. Volatility", f"{risk.get('annualized_volatility', 0):.2%}")
c3.metric("VaR 95% (1-day)", f"{risk.get('var_95_1d', 0):.2%}")
c4.metric("CVaR 95% (1-day)", f"{risk.get('cvar_95_1d', 0):.2%}")
c5.metric("Downside Dev.", f"{risk.get('downside_deviation_annual', 0):.2%}")

st.markdown("---")

# ------------------------------------------------------------------ #
# Drawdown chart
# ------------------------------------------------------------------ #
st.subheader("Drawdown (Underwater Curve)")
from src.analytics.risk import compute_drawdown_series

dd = compute_drawdown_series(port_returns) * 100

fig_dd = go.Figure()
fig_dd.add_trace(
    go.Scatter(
        x=dd.index,
        y=dd.values,
        fill="tozeroy",
        fillcolor="rgba(220,38,38,0.25)",
        line=dict(color="#DC2626", width=1.5),
        name="Drawdown",
    )
)
fig_dd.add_hline(y=0, line_dash="dot", line_color="gray")
fig_dd.update_layout(
    height=300,
    template="plotly_white",
    yaxis_title="Drawdown (%)",
    xaxis_title="",
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig_dd, use_container_width=True)

# ------------------------------------------------------------------ #
# Rolling vol + rolling Sharpe
# ------------------------------------------------------------------ #
col_rvol, col_rsharpe = st.columns(2)

window = st.sidebar.slider("Rolling window (days)", 21, 126, 63, step=21)

rolling_vol = port_returns.rolling(window).std() * np.sqrt(252) * 100
rf_daily = (1 + 0.05) ** (1 / 252) - 1
rolling_sharpe = (
    (port_returns - rf_daily).rolling(window).mean()
    / port_returns.rolling(window).std()
    * np.sqrt(252)
)

with col_rvol:
    st.subheader(f"Rolling {window}d Annualized Volatility")
    fig_rvol = go.Figure()
    fig_rvol.add_trace(
        go.Scatter(
            x=rolling_vol.index,
            y=rolling_vol.values,
            fill="tozeroy",
            fillcolor="rgba(234,88,12,0.15)",
            line=dict(color="#EA580C", width=2),
        )
    )
    fig_rvol.update_layout(
        height=280,
        template="plotly_white",
        yaxis_ticksuffix="%",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_rvol, use_container_width=True)

with col_rsharpe:
    st.subheader(f"Rolling {window}d Sharpe Ratio")
    fig_rs = go.Figure()
    fig_rs.add_trace(
        go.Scatter(
            x=rolling_sharpe.index,
            y=rolling_sharpe.values,
            line=dict(color="#2563EB", width=2),
        )
    )
    fig_rs.add_hline(y=0, line_dash="dot", line_color="gray")
    fig_rs.add_hline(
        y=1.0,
        line_dash="dash",
        line_color="#16A34A",
        annotation_text="Sharpe=1",
        annotation_position="right",
    )
    fig_rs.update_layout(
        height=280,
        template="plotly_white",
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_rs, use_container_width=True)

# ------------------------------------------------------------------ #
# Return distribution
# ------------------------------------------------------------------ #
st.subheader("Return Distribution")
r = port_returns.dropna() * 100
var_95 = risk.get("var_95_1d", 0) * 100
cvar_95 = risk.get("cvar_95_1d", 0) * 100

fig_dist = go.Figure()
fig_dist.add_trace(
    go.Histogram(
        x=r,
        nbinsx=60,
        name="Daily Returns",
        marker_color="rgba(37,99,235,0.6)",
        marker_line_color="white",
        marker_line_width=0.5,
    )
)
fig_dist.add_vline(
    x=-var_95,
    line_dash="dash",
    line_color="#DC2626",
    annotation_text=f"VaR 95%: -{var_95:.2f}%",
    annotation_position="top left",
)
fig_dist.add_vline(
    x=-cvar_95,
    line_dash="dot",
    line_color="#EA580C",
    annotation_text=f"CVaR 95%: -{cvar_95:.2f}%",
    annotation_position="top left",
)
fig_dist.update_layout(
    height=320,
    template="plotly_white",
    xaxis_title="Daily Return (%)",
    yaxis_title="Count",
    margin=dict(l=0, r=0, t=30, b=0),
)
st.plotly_chart(fig_dist, use_container_width=True)

col_sk, col_ku = st.columns(2)
col_sk.metric(
    "Skewness",
    f"{risk.get('return_skewness', 0):.3f}",
    help="Negative = left tail heavier than normal (bad for losses)",
)
col_ku.metric(
    "Excess Kurtosis",
    f"{risk.get('return_excess_kurtosis', 0):.3f}",
    help="Positive = fat tails (more extreme events than normal)",
)

# ------------------------------------------------------------------ #
# Sector concentration
# ------------------------------------------------------------------ #
st.subheader("Sector Concentration")
sector_wts = out.get("sector_weights")
if sector_wts is not None and len(sector_wts) > 0:
    fig_sec = px.bar(
        sector_wts.sort_values("weight"),
        x="weight",
        y="sector",
        orientation="h",
        text=sector_wts.sort_values("weight")["weight"].map(lambda x: f"{x:.1%}"),
        color="weight",
        color_continuous_scale=["#dbeafe", "#2563EB"],
    )
    fig_sec.update_layout(
        height=max(250, len(sector_wts) * 45),
        template="plotly_white",
        xaxis_tickformat=".0%",
        xaxis_title="Weight",
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_sec, use_container_width=True)

# ------------------------------------------------------------------ #
# Full risk table
# ------------------------------------------------------------------ #
with st.expander("📋 Full Risk Metrics Table"):
    risk_df = pd.DataFrame([(k, v) for k, v in risk.items()], columns=["Metric", "Value"])
    st.dataframe(risk_df, use_container_width=True)
