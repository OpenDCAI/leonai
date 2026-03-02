"""Centralized SQLite connection factory.

Single source of truth for connection settings.
All SQLite repos MUST obtain connections through this module.
"""

import sqlite3
from pathlib import Path

WAL_MODE = "WAL"
BUSY_TIMEOUT_MS = 30_000
SYNCHRONOUS = "NORMAL"


def create_connection(
    db_path: Path | str,
    *,
    row_factory: type | None = None,
) -> sqlite3.Connection:
    """Create a SQLite connection with standard Leon settings.

    Guarantees: WAL mode, 30s busy_timeout, check_same_thread=False.
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute(f"PRAGMA journal_mode={WAL_MODE}")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    conn.execute(f"PRAGMA synchronous={SYNCHRONOUS}")
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn
