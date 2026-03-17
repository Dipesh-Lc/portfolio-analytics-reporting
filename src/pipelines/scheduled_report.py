"""
Scheduled reporting job.
Runs the pipeline on a schedule and saves dated reports.

Can be run:
  - Directly:       python -m src.pipelines.scheduled_report
  - Via cron:       0 8 * * 1 cd /path/to/project && python -m src.pipelines.scheduled_report
  - Via Makefile:   make report
"""

import shutil
import time
from datetime import date, datetime
from pathlib import Path

from src.utils.logger import get_logger, setup_logging
from src.utils.paths import REPORTS_DIR, ensure_dirs

setup_logging()
logger = get_logger(__name__)


def run_scheduled_report() -> Path:
    """
    Run the full pipeline and archive the report with a datestamp.

    Returns
    -------
    Path
        Path to the archived dated report.
    """
    ensure_dirs()
    run_date = date.today().isoformat()
    logger.info(f"Scheduled report run starting: {datetime.now().isoformat()}")

    from src.pipelines.run_pipeline import run_pipeline

    try:
        outputs = run_pipeline()
        report_path = outputs["report_path"]

        # Archive with datestamp
        dated_name = f"portfolio_report_{run_date}.html"
        dated_path = REPORTS_DIR / dated_name

        if report_path != dated_path and report_path.exists():
            shutil.copy2(report_path, dated_path)
            logger.info(f"Report archived to: {dated_path}")

        logger.info(f"Scheduled report complete: {dated_path}")
        return dated_path

    except Exception as e:
        logger.error(f"Scheduled report FAILED: {e}", exc_info=True)
        raise


def run_loop(interval_seconds: int = 3600 * 24 * 7) -> None:
    """
    Run scheduled reports in a loop (for always-on deployments).
    Default interval: weekly (7 days).
    """
    logger.info(f"Starting scheduled loop: every {interval_seconds}s")
    while True:
        try:
            run_scheduled_report()
        except Exception as e:
            logger.error(f"Scheduled run failed: {e}")
        logger.info(f"Next run in {interval_seconds}s. Sleeping...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scheduled Portfolio Report")
    parser.add_argument("--loop", action="store_true", help="Run continuously on interval")
    parser.add_argument("--interval", type=int, default=86400 * 7, help="Loop interval in seconds")
    args = parser.parse_args()

    if args.loop:
        run_loop(args.interval)
    else:
        run_scheduled_report()
