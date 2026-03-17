"""
Streamlit Dashboard — Home page.
Entry point for the multi-page portfolio analytics app.

Run: streamlit run src/app/Home.py
"""

import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

st.set_page_config(
    page_title="Portfolio Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
# Sidebar navigation note
# ------------------------------------------------------------------ #
st.sidebar.title("📊 Portfolio Analytics")
st.sidebar.markdown("---")
st.sidebar.markdown("""
    **Navigation**
    - 🏠 Home (this page)
    - 📈 Portfolio Summary
    - ⚠️ Risk Analytics
    - 🔬 Factor Attribution
    """)
st.sidebar.markdown("---")
st.sidebar.caption("Data: Yahoo Finance + Kenneth French Library")

# ------------------------------------------------------------------ #
# Home page content
# ------------------------------------------------------------------ #
st.title("Portfolio Analytics & Risk Platform")
st.markdown("""
    An automated portfolio analytics system that ingests holdings and market data,
    computes performance and risk metrics, estimates Fama-French factor exposures,
    and generates recurring stakeholder-ready reports.
    """)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Data Source", "Yahoo Finance")
    st.metric("Risk Model", "Fama-French 3-Factor")
with col2:
    st.metric("VaR Method", "Historical (95%)")
    st.metric("Factors", "Mkt-RF, SMB, HML")
with col3:
    st.metric("Storage", "SQLite Warehouse")
    st.metric("Report Format", "HTML")

st.markdown("---")

# Run pipeline button
st.subheader("⚡ Run Pipeline")
st.markdown("Click below to fetch the latest prices, compute analytics, and refresh all charts.")

col_run, col_info = st.columns([1, 3])
with col_run:
    run_btn = st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True)

with col_info:
    st.info(
        "This fetches live market data from Yahoo Finance and factor data from Kenneth French's library. "
        "Typical runtime: 20–60 seconds depending on network speed."
    )

if run_btn:
    with st.spinner("Running pipeline... this may take a minute."):
        try:
            from src.pipelines.run_pipeline import run_pipeline

            outputs = run_pipeline()
            st.success(
                f"✅ Pipeline complete! "
                f"Cumulative return: {outputs['perf_metrics'].get('cumulative_return', 0):.2%} | "
                f"Sharpe: {outputs['perf_metrics'].get('sharpe_ratio', 0):.2f}"
            )
            st.session_state["pipeline_outputs"] = outputs
            st.balloons()
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)

# Show report link if available
from src.utils.paths import REPORTS_DIR

reports = sorted(REPORTS_DIR.glob("*.html"), reverse=True)
if reports:
    st.markdown("---")
    st.subheader("📄 Latest Reports")
    for r in reports[:5]:
        st.markdown(f"📋 `{r.name}` — {r.stat().st_mtime:.0f}")

st.markdown("---")
st.caption("Portfolio Analytics Platform | For internal use only. Not investment advice.")
