"""
Report generation: renders analytics into HTML (and optionally Markdown/PDF).
Packages all analytics outputs into a stakeholder-ready report.
"""

import base64
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from src.utils.logger import get_logger
from src.utils.paths import REPORTS_DIR, TEMPLATES_DIR

logger = get_logger(__name__)


def _img_to_base64(path: Path) -> str:
    """Embed image as base64 data URI for self-contained HTML."""
    if path and path.exists():
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{data}"
    return ""


def generate_html_report(
    holdings: pd.DataFrame,
    daily_returns: pd.Series,
    perf_metrics: dict,
    risk_metrics: dict,
    factor_result,
    attribution: dict,
    chart_paths: dict,
    sector_weights: Optional[pd.DataFrame] = None,
    portfolio_name: str = "Sample Multi-Asset Portfolio",
    risk_free_rate: float = 0.05,
    var_confidence: float = 0.95,
    trading_days: int = 252,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a self-contained HTML analytics report.

    Parameters
    ----------
    holdings : pd.DataFrame
        Raw holdings table for display.
    daily_returns : pd.Series
        Daily portfolio returns.
    perf_metrics : dict
        Output from compute_performance_metrics().
    risk_metrics : dict
        Output from compute_risk_metrics().
    factor_result : FactorModelResult
        Output from run_factor_regression().
    attribution : dict
        Output from interpret_factor_exposures().
    chart_paths : dict
        Dict of chart_name -> Path from generate_all_charts().
    output_path : Path, optional
        Where to save the report HTML.

    Returns
    -------
    Path
        Path to the generated HTML report.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_date = date.today().isoformat()
    output_path = output_path or (REPORTS_DIR / f"portfolio_report_{report_date}.html")

    # Embed charts as base64 for self-contained HTML
    embedded_charts = {
        name: _img_to_base64(path) for name, path in chart_paths.items() if path and path.exists()
    }

    # Render template
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    try:
        template = env.get_template("report.html")
    except Exception:
        logger.warning("Template not found, using minimal fallback")
        return _generate_minimal_html_report(
            perf_metrics, risk_metrics, attribution, output_path, report_date, portfolio_name
        )

    # Date range
    r = daily_returns.dropna()
    period_start = r.index.min().date().isoformat() if len(r) > 0 else "N/A"
    period_end = r.index.max().date().isoformat() if len(r) > 0 else "N/A"

    # Wrap metrics as simple objects for template access
    class DictWrapper:
        def __init__(self, d):
            self._d = d

        def __getattr__(self, k):
            return self._d.get(k, "N/A")

        def __getitem__(self, k):
            return self._d.get(k, "N/A")

    html = template.render(
        portfolio_name=portfolio_name,
        report_date=report_date,
        period_start=period_start,
        period_end=period_end,
        n_assets=holdings["ticker"].nunique(),
        perf=DictWrapper(perf_metrics),
        risk=DictWrapper(risk_metrics),
        factor_model=factor_result,
        attribution=attribution,
        holdings=holdings.drop_duplicates("ticker", keep="last"),
        charts=embedded_charts,
        risk_free_rate=risk_free_rate,
        var_confidence=int(var_confidence * 100),
        trading_days=trading_days,
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"HTML report generated: {output_path}")
    return output_path


def _generate_minimal_html_report(
    perf_metrics: dict,
    risk_metrics: dict,
    attribution: dict,
    output_path: Path,
    report_date: str,
    portfolio_name: str,
) -> Path:
    """Fallback minimal HTML report without Jinja template."""
    lines = [
        f"<html><body><h1>{portfolio_name}</h1>",
        f"<p>Report Date: {report_date}</p>",
        "<h2>Performance</h2><pre>",
        *[f"{k}: {v}" for k, v in perf_metrics.items()],
        "</pre><h2>Risk</h2><pre>",
        *[f"{k}: {v}" for k, v in risk_metrics.items()],
        "</pre></body></html>",
    ]
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    return output_path
