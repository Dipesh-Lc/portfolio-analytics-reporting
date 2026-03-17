"""
Main pipeline orchestrator.
Runs the full end-to-end portfolio analytics workflow:
  1. Load holdings
  2. Fetch prices + factors
  3. Validate all data
  4. Build prices panel + compute returns
  5. Compute portfolio weights + P&L
  6. Compute performance metrics
  7. Compute risk metrics
  8. Run factor regression + attribution
  9. Generate charts
  10. Generate HTML report
  11. Store results in warehouse

Usage:
    python -m src.pipelines.run_pipeline
    python -m src.pipelines.run_pipeline --holdings data/samples/portfolio_holdings.csv
    python -m src.pipelines.run_pipeline --start-date 2024-01-01 --no-warehouse
"""

import argparse
import sys
from datetime import date
from pathlib import Path

# Allow running as __main__ from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import yaml

from src.utils.logger import get_logger, setup_logging
from src.utils.paths import CONFIG_FILE, HOLDINGS_FILE, ensure_dirs

setup_logging()
logger = get_logger(__name__)


def load_config() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f)
    return {}


def run_pipeline(
    holdings_path: Path = HOLDINGS_FILE,
    start_date: str = "2024-01-01",
    end_date: str | None = None,
    use_warehouse: bool = True,
    report_only: bool = False,
) -> dict:
    """
    Execute the full portfolio analytics pipeline.

    Returns
    -------
    dict
        All computed outputs: returns, metrics, factor results, report path.
    """
    ensure_dirs()
    cfg = load_config()

    end_date = end_date or date.today().isoformat()
    start_date = cfg.get("data", {}).get("price_start_date", start_date)
    risk_free_annual = cfg.get("analytics", {}).get("risk_free_annual", 0.05)
    var_confidence = cfg.get("analytics", {}).get("var_confidence", 0.95)
    trading_days = cfg.get("analytics", {}).get("trading_days_year", 252)
    portfolio_name = cfg.get("portfolio", {}).get("name", "Portfolio")

    logger.info("=" * 60)
    logger.info(f"PORTFOLIO ANALYTICS PIPELINE - {date.today()}")
    logger.info("=" * 60)

    # ------------------------------------------------------------------ #
    # Phase 1: Ingest
    # ------------------------------------------------------------------ #
    logger.info("[1/10] Loading holdings...")
    from src.ingestion.load_holdings import get_tickers, load_holdings

    holdings = load_holdings(holdings_path)
    tickers = get_tickers(holdings)
    logger.info(f"  -> {len(holdings)} rows, {len(tickers)} tickers: {tickers}")

    logger.info("[2/10] Fetching prices from Yahoo Finance...")
    from src.ingestion.fetch_prices import fetch_prices

    prices = fetch_prices(tickers, start_date=start_date, end_date=end_date)

    logger.info("[3/10] Fetching Fama-French factors...")
    from src.ingestion.fetch_factors import fetch_factors

    factors = fetch_factors(start_date=start_date, end_date=end_date)

    # ------------------------------------------------------------------ #
    # Phase 2: Validate
    # ------------------------------------------------------------------ #
    logger.info("[4/10] Validating data...")
    from src.validation.data_checks import validate_factors, validate_holdings, validate_prices

    h_result = validate_holdings(holdings)
    validate_prices(prices, tickers)
    validate_factors(factors, prices)

    if not h_result.is_valid:
        logger.error("Holdings validation failed - check data quality")
        logger.error(h_result.summary())
        # Don't abort for warnings; abort only on errors
        if h_result.errors:
            raise ValueError("Holdings have critical errors. Fix before proceeding.")

    # ------------------------------------------------------------------ #
    # Phase 3: Warehouse
    # ------------------------------------------------------------------ #
    if use_warehouse:
        logger.info("[5/10] Loading data into warehouse...")
        from src.warehouse.db import get_engine, init_schema
        from src.warehouse.load import load_factors as wh_factors
        from src.warehouse.load import load_holdings as wh_holdings
        from src.warehouse.load import load_prices as wh_prices

        engine = get_engine()
        init_schema(engine)
        try:
            wh_holdings(holdings, engine)
            wh_prices(prices, engine)
            wh_factors(factors, engine)
        except Exception as e:
            logger.warning(f"Warehouse load partial failure (non-fatal): {e}")
    else:
        logger.info("[5/10] Skipping warehouse (--no-warehouse)")

    # ------------------------------------------------------------------ #
    # Phase 4: Processing
    # ------------------------------------------------------------------ #
    logger.info("[6/10] Building prices panel + computing returns...")
    from src.processing.build_prices_panel import build_prices_panel
    from src.processing.positions import (
        compute_market_values,
        compute_pnl,
        compute_portfolio_weights,
        compute_sector_weights,
    )
    from src.processing.returns import (
        compute_asset_returns,
        compute_cumulative_returns,
        compute_portfolio_returns,
    )

    panel = build_prices_panel(prices, tickers=tickers)
    asset_returns = compute_asset_returns(panel)

    market_values = compute_market_values(holdings, panel)
    weights = compute_portfolio_weights(market_values)
    pnl_df = compute_pnl(market_values, holdings)
    sector_wts = compute_sector_weights(holdings, market_values)

    port_returns = compute_portfolio_returns(asset_returns, weights)
    cum_returns = compute_cumulative_returns(port_returns)

    logger.info(
        f"  -> Portfolio returns: {len(port_returns)} days, "
        f"total return = {cum_returns.iloc[-1]:.2%}"
    )

    # ------------------------------------------------------------------ #
    # Phase 5: Analytics
    # ------------------------------------------------------------------ #
    logger.info("[7/10] Computing performance metrics...")
    from src.analytics.performance import compute_performance_metrics

    perf_metrics = compute_performance_metrics(
        port_returns,
        risk_free_annual=risk_free_annual,
        trading_days=trading_days,
    )

    logger.info("[8/10] Computing risk metrics...")
    from src.analytics.risk import compute_risk_metrics

    risk_metrics = compute_risk_metrics(
        port_returns,
        confidence=var_confidence,
        trading_days=trading_days,
        risk_free_annual=risk_free_annual,
    )

    logger.info("[9/10] Running Fama-French factor regression...")
    factor_result = None
    attribution = {}
    try:
        from src.analytics.attribution import interpret_factor_exposures
        from src.analytics.factor_model import run_factor_regression

        factor_result = run_factor_regression(port_returns, factors, trading_days=trading_days)
        attribution = interpret_factor_exposures(factor_result)
        logger.info(f"  -> Style: {attribution['style_summary']}")
    except Exception as e:
        logger.warning(f"Factor regression skipped: {e}")
        attribution = {
            "style_summary": "Factor regression unavailable",
            "commentary": [str(e)],
            "factor_loadings": {},
            "r_squared": 0,
            "attribution_table": __import__("pandas").DataFrame(),
        }

    # ------------------------------------------------------------------ #
    # Phase 6: Store analytics snapshot
    # ------------------------------------------------------------------ #
    if use_warehouse:
        try:
            from src.warehouse.load import load_analytics_snapshot

            all_metrics = {**perf_metrics, **risk_metrics}
            if factor_result:
                all_metrics.update(
                    {
                        "factor_alpha": factor_result.alpha,
                        "factor_beta_mkt": factor_result.beta_mkt,
                        "factor_beta_smb": factor_result.beta_smb,
                        "factor_beta_hml": factor_result.beta_hml,
                        "factor_r_squared": factor_result.r_squared,
                    }
                )
            load_analytics_snapshot(all_metrics, date.today().isoformat(), engine)

            # Store portfolio returns
            import pandas as pd

            ret_df = pd.DataFrame(
                {
                    "date": port_returns.index,
                    "daily_return": port_returns.values,
                    "cumulative_return": cum_returns.values,
                    "daily_pnl": pnl_df["daily_pnl"].reindex(port_returns.index).values,
                    "cumulative_pnl": pnl_df["cumulative_pnl"].reindex(port_returns.index).values,
                    "portfolio_value": pnl_df["portfolio_value"].reindex(port_returns.index).values,
                }
            )
            from src.warehouse.load import load_portfolio_returns

            load_portfolio_returns(ret_df, engine)
        except Exception as e:
            logger.warning(f"Analytics snapshot storage failed (non-fatal): {e}")

    # ------------------------------------------------------------------ #
    # Phase 7: Charts + Report
    # ------------------------------------------------------------------ #
    logger.info("[10/10] Generating charts and report...")
    from src.reporting.charts import generate_all_charts
    from src.reporting.generate_report import generate_html_report

    chart_paths = generate_all_charts(
        daily_returns=port_returns,
        factor_result=factor_result,
        sector_weights=sector_wts,
    )

    report_path = generate_html_report(
        holdings=holdings,
        daily_returns=port_returns,
        perf_metrics=perf_metrics,
        risk_metrics=risk_metrics,
        factor_result=factor_result,
        attribution=attribution,
        chart_paths=chart_paths,
        sector_weights=sector_wts,
        portfolio_name=portfolio_name,
        risk_free_rate=risk_free_annual,
        var_confidence=var_confidence,
        trading_days=trading_days,
    )

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Cumulative return : {perf_metrics.get('cumulative_return', 0):.2%}")
    logger.info(f"  Annualized return : {perf_metrics.get('annualized_return', 0):.2%}")
    logger.info(f"  Sharpe ratio      : {perf_metrics.get('sharpe_ratio', 0):.2f}")
    logger.info(f"  Max drawdown      : {risk_metrics.get('max_drawdown', 0):.2%}")
    logger.info(f"  VaR 95% (1d)      : {risk_metrics.get('var_95_1d', 0):.2%}")
    if factor_result:
        logger.info(f"  Factor beta (mkt) : {factor_result.beta_mkt:.3f}")
        logger.info(f"  Factor R^2        : {factor_result.r_squared:.3f}")
    logger.info(f"  Report            : {report_path}")
    logger.info(f"  Charts            : {len(chart_paths)} saved to artifacts/figures/")
    logger.info("")

    return {
        "holdings": holdings,
        "prices": prices,
        "factors": factors,
        "panel": panel,
        "asset_returns": asset_returns,
        "portfolio_returns": port_returns,
        "cumulative_returns": cum_returns,
        "market_values": market_values,
        "weights": weights,
        "pnl": pnl_df,
        "sector_weights": sector_wts,
        "perf_metrics": perf_metrics,
        "risk_metrics": risk_metrics,
        "factor_result": factor_result,
        "attribution": attribution,
        "chart_paths": chart_paths,
        "report_path": report_path,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Portfolio Analytics Pipeline")
    parser.add_argument("--holdings", type=Path, default=HOLDINGS_FILE)
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--no-warehouse", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(
        holdings_path=args.holdings,
        start_date=args.start_date,
        end_date=args.end_date,
        use_warehouse=not args.no_warehouse,
        report_only=args.report_only,
    )
