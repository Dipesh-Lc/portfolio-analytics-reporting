"""
Chart generation for portfolio analytics reporting.
Saves figures to artifacts/figures/.
"""

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # Non-interactive backend for server use
from pathlib import Path
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from src.utils.logger import get_logger
from src.utils.paths import FIGURES_DIR

logger = get_logger(__name__)

# Style constants
PALETTE = {
    "blue": "#2563EB",
    "red": "#DC2626",
    "green": "#16A34A",
    "orange": "#EA580C",
    "gray": "#6B7280",
    "light_gray": "#F3F4F6",
    "dark": "#111827",
}

plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
        "font.family": "sans-serif",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def _save(fig, name: str, figures_dir: Path = FIGURES_DIR) -> Path:
    figures_dir.mkdir(parents=True, exist_ok=True)
    path = figures_dir / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info(f"Chart saved: {path}")
    return path


def plot_cumulative_returns(
    daily_returns: pd.Series,
    title: str = "Portfolio Cumulative Return",
    benchmark_returns: Optional[pd.Series] = None,
) -> Path:
    """Equity curve: portfolio NAV growth from 1.0."""
    cumulative = (1 + daily_returns).cumprod()

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        cumulative.index, cumulative.values, color=PALETTE["blue"], linewidth=2, label="Portfolio"
    )

    if benchmark_returns is not None:
        bench_cum = (1 + benchmark_returns).cumprod()
        ax.plot(
            bench_cum.index,
            bench_cum.values,
            color=PALETTE["gray"],
            linewidth=1.5,
            linestyle="--",
            label="Benchmark (SPY)",
        )

    ax.axhline(1.0, color=PALETTE["gray"], linewidth=0.8, linestyle=":")
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Growth of $1", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.2f}x"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    ax.legend()
    ax.set_xlabel("")

    # Shade below 1.0
    ax.fill_between(
        cumulative.index,
        cumulative.values,
        1.0,
        where=(cumulative.values < 1.0),
        alpha=0.15,
        color=PALETTE["red"],
        label="_nolegend_",
    )

    return _save(fig, "cumulative_returns")


def plot_drawdown(daily_returns: pd.Series) -> Path:
    """Drawdown (underwater) curve."""
    from src.analytics.risk import compute_drawdown_series

    dd = compute_drawdown_series(daily_returns)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(dd.index, dd.values * 100, 0, color=PALETTE["red"], alpha=0.4)
    ax.plot(dd.index, dd.values * 100, color=PALETTE["red"], linewidth=1)
    ax.set_title("Portfolio Drawdown", fontsize=14, fontweight="bold", pad=12)
    ax.set_ylabel("Drawdown (%)", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)

    max_dd = dd.min()
    max_dd_date = dd.idxmin()
    ax.annotate(
        f"Max DD: {max_dd:.1%}",
        xy=(max_dd_date, max_dd * 100),
        xytext=(10, -20),
        textcoords="offset points",
        fontsize=9,
        color=PALETTE["red"],
    )
    return _save(fig, "drawdown")


def plot_rolling_volatility(
    daily_returns: pd.Series,
    window: int = 63,
) -> Path:
    """Rolling annualized volatility chart."""
    rolling_vol = daily_returns.rolling(window).std() * np.sqrt(252) * 100

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(rolling_vol.index, rolling_vol.values, color=PALETTE["orange"], linewidth=1.5)
    ax.fill_between(rolling_vol.index, rolling_vol.values, alpha=0.2, color=PALETTE["orange"])
    ax.set_title(
        f"Rolling {window}-Day Annualized Volatility", fontsize=14, fontweight="bold", pad=12
    )
    ax.set_ylabel("Volatility (% p.a.)", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y, _: f"{y:.1f}%"))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    return _save(fig, "rolling_volatility")


def plot_monthly_returns_heatmap(daily_returns: pd.Series) -> Path:
    """Monthly returns heatmap."""
    from src.analytics.performance import compute_monthly_returns

    monthly = compute_monthly_returns(daily_returns)

    # Drop Annual column for heatmap
    heatmap_data = monthly.drop(columns=["Annual"], errors="ignore") * 100

    fig, ax = plt.subplots(figsize=(14, max(4, len(heatmap_data) * 0.6)))

    # Color limits symmetric around 0
    vmax = max(abs(heatmap_data.values[~np.isnan(heatmap_data.values)]).max(), 0.1)
    im = ax.imshow(heatmap_data.values, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(len(heatmap_data.columns)))
    ax.set_xticklabels(heatmap_data.columns, fontsize=10)
    ax.set_yticks(range(len(heatmap_data.index)))
    ax.set_yticklabels(heatmap_data.index.astype(str), fontsize=10)

    # Annotate cells
    for i in range(len(heatmap_data.index)):
        for j in range(len(heatmap_data.columns)):
            val = heatmap_data.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center", fontsize=8, color="black")

    plt.colorbar(im, ax=ax, label="Monthly Return (%)")
    ax.set_title("Monthly Returns Heatmap", fontsize=14, fontweight="bold", pad=12)
    ax.grid(False)
    fig.tight_layout()
    return _save(fig, "monthly_returns_heatmap")


def plot_return_distribution(daily_returns: pd.Series) -> Path:
    """Return distribution histogram with VaR lines."""
    from scipy import stats

    from src.analytics.risk import compute_cvar_historical, compute_var_historical

    r = daily_returns.dropna() * 100
    var_95 = compute_var_historical(daily_returns) * 100
    cvar_95 = compute_cvar_historical(daily_returns) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    n, bins, _ = ax.hist(
        r,
        bins=60,
        color=PALETTE["blue"],
        alpha=0.6,
        edgecolor="white",
        density=True,
        label="Daily Returns",
    )

    # Normal overlay
    mu, sigma = r.mean(), r.std()
    x = np.linspace(r.min(), r.max(), 200)
    ax.plot(
        x,
        stats.norm.pdf(x, mu, sigma),
        color=PALETTE["dark"],
        linewidth=1.5,
        linestyle="--",
        label="Normal dist.",
    )

    ax.axvline(-var_95, color=PALETTE["red"], linewidth=1.5, label=f"VaR 95% ({-var_95:.2f}%)")
    ax.axvline(
        -cvar_95,
        color=PALETTE["orange"],
        linewidth=1.5,
        linestyle="--",
        label=f"CVaR 95% ({-cvar_95:.2f}%)",
    )

    ax.set_title("Daily Return Distribution", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Daily Return (%)", fontsize=11)
    ax.set_ylabel("Density", fontsize=11)
    ax.legend(fontsize=9)
    return _save(fig, "return_distribution")


def plot_factor_loadings(factor_result) -> Path:
    """Bar chart of Fama-French factor loadings."""
    betas = {
        "Market (beta)": factor_result.beta_mkt,
        "Size (SMB)": factor_result.beta_smb,
        "Value (HML)": factor_result.beta_hml,
    }
    colors = [PALETTE["blue"] if v > 0 else PALETTE["red"] for v in betas.values()]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        list(betas.keys()), list(betas.values()), color=colors, width=0.5, edgecolor="white"
    )
    ax.axhline(0, color=PALETTE["dark"], linewidth=0.8)

    for bar, val in zip(bars, betas.values()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + (0.02 if val >= 0 else -0.04),
            f"{val:.3f}",
            ha="center",
            va="bottom" if val >= 0 else "top",
            fontsize=11,
            fontweight="bold",
        )

    ax.set_title(
        f"Fama-French Factor Loadings  (R^2 = {factor_result.r_squared:.1%})",
        fontsize=14,
        fontweight="bold",
        pad=12,
    )
    ax.set_ylabel("Factor Beta", fontsize=11)
    ax.set_ylim(
        min(list(betas.values())) - 0.3,
        max(list(betas.values())) + 0.3,
    )
    ax.grid(axis="x", alpha=0)
    return _save(fig, "factor_loadings")


def plot_sector_weights(sector_weights: pd.DataFrame) -> Path:
    """Horizontal bar chart of sector weights."""
    df = sector_weights.sort_values("weight")
    colors = [PALETTE["blue"]] * len(df)

    fig, ax = plt.subplots(figsize=(8, max(4, len(df) * 0.5)))
    bars = ax.barh(df["sector"], df["weight"] * 100, color=colors, edgecolor="white")

    for bar, val in zip(bars, df["weight"] * 100):
        ax.text(
            val + 0.3, bar.get_y() + bar.get_height() / 2, f"{val:.1f}%", va="center", fontsize=10
        )

    ax.set_title("Portfolio Sector Allocation", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Weight (%)", fontsize=11)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.grid(axis="y", alpha=0)
    return _save(fig, "sector_weights")


def generate_all_charts(
    daily_returns: pd.Series,
    factor_result=None,
    sector_weights: Optional[pd.DataFrame] = None,
) -> dict[str, Path]:
    """
    Generate all standard charts. Returns dict of name -> Path.
    """
    paths = {}
    logger.info("Generating charts...")

    try:
        paths["cumulative_returns"] = plot_cumulative_returns(daily_returns)
    except Exception as e:
        logger.error(f"cumulative_returns chart failed: {e}")

    try:
        paths["drawdown"] = plot_drawdown(daily_returns)
    except Exception as e:
        logger.error(f"drawdown chart failed: {e}")

    try:
        paths["rolling_volatility"] = plot_rolling_volatility(daily_returns)
    except Exception as e:
        logger.error(f"rolling_volatility chart failed: {e}")

    try:
        paths["monthly_returns_heatmap"] = plot_monthly_returns_heatmap(daily_returns)
    except Exception as e:
        logger.error(f"monthly_returns_heatmap chart failed: {e}")

    try:
        paths["return_distribution"] = plot_return_distribution(daily_returns)
    except Exception as e:
        logger.error(f"return_distribution chart failed: {e}")

    if factor_result is not None:
        try:
            paths["factor_loadings"] = plot_factor_loadings(factor_result)
        except Exception as e:
            logger.error(f"factor_loadings chart failed: {e}")

    if sector_weights is not None:
        try:
            paths["sector_weights"] = plot_sector_weights(sector_weights)
        except Exception as e:
            logger.error(f"sector_weights chart failed: {e}")

    logger.info(f"Generated {len(paths)} charts")
    return paths
