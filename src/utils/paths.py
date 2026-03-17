"""
Centralized path management for the project.
All modules should import paths from here to ensure consistency.
"""

from pathlib import Path

# Project root = parent of src/
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Main directories
DATA_DIR = PROJECT_ROOT / "data"
SRC_DIR = PROJECT_ROOT / "src"
CONFIGS_DIR = PROJECT_ROOT / "configs"
SQL_DIR = PROJECT_ROOT / "sql"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
DOCS_DIR = PROJECT_ROOT / "docs"

# Data subdirectories
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLES_DIR = DATA_DIR / "samples"

# Artifact subdirectories
REPORTS_DIR = ARTIFACTS_DIR / "reports"
FIGURES_DIR = ARTIFACTS_DIR / "figures"
LOGS_DIR = ARTIFACTS_DIR / "logs"

# Key files
CONFIG_FILE = CONFIGS_DIR / "config.yaml"
LOGGING_CONFIG_FILE = CONFIGS_DIR / "logging.yaml"
HOLDINGS_FILE = SAMPLES_DIR / "portfolio_holdings.csv"
DB_FILE = DATA_DIR / "portfolio.db"
SCHEMA_FILE = SQL_DIR / "schema.sql"

# Reporting templates
TEMPLATES_DIR = SRC_DIR / "reporting" / "templates"


def ensure_dirs():
    """Create all required directories if they don't exist."""
    for d in [RAW_DIR, INTERIM_DIR, PROCESSED_DIR, REPORTS_DIR, FIGURES_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
