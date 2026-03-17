"""
Streamlit Page: Portfolio Summary
Shows cumulative returns, performance metrics, monthly heatmap, and P&L.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

st.set_page_config(page_title="Portfolio Summary", page_icon="📈", layout="wide")
st.title("📈 Portfolio Summary")

# ------------------------------------------------------------------ #
# Load or run pipeline
# ------------------------------------------------------------------ #


@st.cache_data(ttl=3600, show_spinner="Fetching data...")
def get_pipeline_outputs():
    from src.pipelines.run_pipeline import run_pipeline

    return run_pipeline()


if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

try:
    if "pipeline_outputs" not in st.session_state:
        st.warning("Run the pipeline from the Home page first.")
        st.stop()
    out = st.session_state["pipeline_outputs"]

except Exception as e:
    st.error(f"Could not load data: {e}")
    st.stop()

perf = out["perf_metrics"]
port_returns = out["portfolio_returns"]
cum_returns = out["cumulative_returns"]
pnl = out["pnl"]

# ------------------------------------------------------------------ #
# Metric cards row
# ------------------------------------------------------------------ #
st.subheader("Key Performance Metrics")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Cumulative Return", f"{perf.get('cumulative_return', 0):.2%}")
c2.metric("Annualized Return", f"{perf.get('annualized_return', 0):.2%}")
c3.metric("Annualized Vol", f"{perf.get('annualized_volatility', 0):.2%}")
c4.metric("Sharpe Ratio", f"{perf.get('sharpe_ratio', 0):.2f}")
c5.metric("Sortino Ratio", f"{perf.get('sortino_ratio', 0):.2f}")
c6.metric("Hit Ratio", f"{perf.get('hit_ratio', 0):.1%}")

st.markdown("---")

# ------------------------------------------------------------------ #
# Equity curve
# ------------------------------------------------------------------ #
st.subheader("Equity Curve")
equity = (1 + port_returns).cumprod().rename("Portfolio (Growth of $1)")

import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=equity.index,
        y=equity.values,
        name="Portfolio",
        line=dict(color="#2563EB", width=2),
        fill="tonexty",
        fillcolor="rgba(37,99,235,0.08)",
    )
)
fig.add_hline(y=1.0, line_dash="dot", line_color="gray", line_width=1)
fig.update_layout(
    height=380,
    xaxis_title="",
    yaxis_title="Growth of $1",
    template="plotly_white",
    margin=dict(l=0, r=0, t=10, b=0),
    legend=dict(orientation="h"),
)
fig.update_yaxes(tickformat=".2f")
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ #
# Portfolio value + P&L
# ------------------------------------------------------------------ #
col_val, col_pnl = st.columns(2)

with col_val:
    st.subheader("Portfolio Value (NAV)")
    nav = pnl["portfolio_value"].dropna()
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=nav.index,
            y=nav.values,
            line=dict(color="#16A34A", width=2),
            fill="tozeroy",
            fillcolor="rgba(22,163,74,0.08)",
        )
    )
    fig2.update_layout(
        height=280,
        template="plotly_white",
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_pnl:
    st.subheader("Cumulative P&L")
    cpnl = pnl["cumulative_pnl"].dropna()
    colors = ["#16A34A" if v >= 0 else "#DC2626" for v in cpnl.values]
    fig3 = go.Figure()
    fig3.add_trace(
        go.Scatter(
            x=cpnl.index,
            y=cpnl.values,
            line=dict(color="#2563EB", width=2),
            fill="tozeroy",
            fillcolor="rgba(37,99,235,0.08)",
        )
    )
    fig3.add_hline(y=0, line_dash="dot", line_color="gray")
    fig3.update_layout(
        height=280,
        template="plotly_white",
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_tickprefix="$",
        yaxis_tickformat=",.0f",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------------ #
# Monthly returns heatmap
# ------------------------------------------------------------------ #
st.subheader("Monthly Returns")
try:
    from src.analytics.performance import compute_monthly_returns

    monthly = compute_monthly_returns(port_returns) * 100

    # Format as colored dataframe
    def color_return(val):
        if pd.isna(val):
            return ""
        color = "#d1fae5" if val > 0 else "#fee2e2" if val < 0 else "#f3f4f6"
        return f"background-color: {color}"

    fmt = {c: "{:.2f}%" for c in monthly.columns}
    styled = monthly.style.format(fmt, na_rep="—").map(color_return)
    st.dataframe(styled, use_container_width=True)
except Exception as e:
    st.warning(f"Monthly heatmap unavailable: {e}")

# ------------------------------------------------------------------ #
# Holdings table
# ------------------------------------------------------------------ #
st.subheader("Holdings")
holdings = out["holdings"].drop_duplicates("ticker", keep="last")

# Add latest prices and market value
panel = out["panel"]
latest_prices = panel.iloc[-1].rename("current_price")
mv = out["market_values"].iloc[-1].rename("market_value")
wts = out["weights"].iloc[-1].rename("weight")

holdings_display = (
    holdings.set_index("ticker").join([latest_prices, mv, wts], how="left").reset_index()
)
holdings_display["unrealized_pnl"] = (
    holdings_display["current_price"] - holdings_display["avg_cost"]
) * holdings_display["quantity"]

display_cols = [
    "ticker",
    "asset_class",
    "sector",
    "quantity",
    "avg_cost",
    "current_price",
    "market_value",
    "weight",
    "unrealized_pnl",
]
holdings_display = holdings_display[[c for c in display_cols if c in holdings_display.columns]]


def fmt_pnl(val):
    if pd.isna(val):
        return ""
    color = "#16a34a" if val >= 0 else "#dc2626"
    return f"color: {color}"


styled_h = holdings_display.style.format(
    {
        "avg_cost": "${:.2f}",
        "current_price": "${:.2f}",
        "market_value": "${:,.0f}",
        "weight": "{:.1%}",
        "unrealized_pnl": "${:+,.0f}",
    },
    na_rep="—",
).applymap(fmt_pnl, subset=["unrealized_pnl"])
st.dataframe(styled_h, use_container_width=True)
