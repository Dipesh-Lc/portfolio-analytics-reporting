"""
Centralized logging setup.
"""

import logging
import logging.config
from pathlib import Path

import yaml

from src.utils.paths import LOGGING_CONFIG_FILE, LOGS_DIR


def setup_logging(default_level: int = logging.INFO) -> None:
    """Configure logging from YAML config or fall back to basic config."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if LOGGING_CONFIG_FILE.exists():
        with open(LOGGING_CONFIG_FILE, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        for handler in config.get("handlers", {}).values():
            if "filename" in handler:
                Path(handler["filename"]).parent.mkdir(parents=True, exist_ok=True)

        logging.config.dictConfig(config)
    else:
        logging.basicConfig(
            level=default_level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Call setup_logging() once at pipeline start."""
    return logging.getLogger(name)
