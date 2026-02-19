"""Shared sandbox DB constants."""

import os
from pathlib import Path

# @@@env-at-import - This is evaluated at import time. For web backend, prefer exporting env vars before process start.
DEFAULT_DB_PATH = Path(os.getenv("LEON_SANDBOX_DB_PATH") or (Path.home() / ".leon" / "sandbox.db"))
