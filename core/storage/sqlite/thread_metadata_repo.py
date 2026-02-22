"""SQLite thread metadata repository."""

import sqlite3
from pathlib import Path

from core.storage.interfaces import ThreadMetadataRepo


class SQLiteThreadMetadataRepo(ThreadMetadataRepo):
    """SQLite implementation of thread metadata persistence."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def save_thread_metadata(self, thread_id: str, sandbox_type: str, cwd: str | None) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            # @@@thread-metadata-upsert-preserve-model - metadata updates must not overwrite an already-persisted model.
            conn.execute(
                "INSERT INTO thread_metadata (thread_id, sandbox_type, cwd) VALUES (?, ?, ?) "
                "ON CONFLICT(thread_id) DO UPDATE SET sandbox_type = excluded.sandbox_type, cwd = excluded.cwd",
                (thread_id, sandbox_type, cwd),
            )
            conn.commit()

    def save_thread_model(self, thread_id: str, model: str) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("UPDATE thread_metadata SET model = ? WHERE thread_id = ?", (model, thread_id))
            conn.commit()

    def lookup_thread_model(self, thread_id: str) -> str | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute("SELECT model FROM thread_metadata WHERE thread_id = ?", (thread_id,)).fetchone()
            return row[0] if row and row[0] else None

    def lookup_thread_metadata(self, thread_id: str) -> tuple[str, str | None] | None:
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT sandbox_type, cwd FROM thread_metadata WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
            return (row[0], row[1]) if row else None
