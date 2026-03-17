"""
SQLite database connection and schema management.
"""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.utils.logger import get_logger
from src.utils.paths import DB_FILE, SCHEMA_FILE

logger = get_logger(__name__)

_engine: Engine | None = None


def get_engine(db_path: Path = DB_FILE) -> Engine:
    """Get or create the SQLAlchemy engine (singleton per process)."""
    global _engine
    if _engine is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_path}"
        _engine = create_engine(url, echo=False, future=True)
        logger.info(f"Connected to database: {db_path}")
    return _engine


def init_schema(engine: Engine | None = None) -> None:
    """Create tables from schema.sql if they don't exist."""
    engine = engine or get_engine()

    if not SCHEMA_FILE.exists():
        logger.warning(f"Schema file not found: {SCHEMA_FILE}")
        return

    sql = SCHEMA_FILE.read_text()

    with engine.begin() as conn:
        raw = conn.connection  # access sqlite3 connection
        raw.executescript(sql)

    logger.info("Database schema initialized")


def get_connection(db_path: Path = DB_FILE) -> sqlite3.Connection:
    """Get a raw sqlite3 connection (useful for pandas read_sql)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)
