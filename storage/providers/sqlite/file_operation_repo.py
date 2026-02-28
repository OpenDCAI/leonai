"""SQLite repository for file_operations persistence."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

from storage.models import FileOperationRow  # noqa: F401 — re-exported for backwards compat


class SQLiteFileOperationRepo:
    """Repository boundary for file_operations table."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / ".leon" / "leon.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def record(
        self,
        thread_id: str,
        checkpoint_id: str,
        operation_type: str,
        file_path: str,
        before_content: str | None,
        after_content: str,
        changes: list[dict] | None = None,
    ) -> str:
        op_id = str(uuid.uuid4())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO file_operations
                (id, thread_id, checkpoint_id, timestamp, operation_type,
                 file_path, before_content, after_content, changes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    op_id,
                    thread_id,
                    checkpoint_id,
                    time.time(),
                    operation_type,
                    file_path,
                    before_content,
                    after_content,
                    json.dumps(changes) if changes else None,
                    "applied",
                ),
            )
            conn.commit()
        return op_id

    def close(self) -> None:
        """Compatibility no-op for protocol parity."""
        return None

    def get_operations_for_thread(self, thread_id: str, status: str = "applied") -> list[FileOperationRow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM file_operations
                WHERE thread_id = ? AND status = ?
                ORDER BY timestamp ASC
                """,
                (thread_id, status),
            )
            rows = cursor.fetchall()
        return [self._row_to_operation(row) for row in rows]

    def get_operations_after_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT MIN(timestamp) as ts FROM file_operations
                WHERE thread_id = ? AND checkpoint_id = ?
                """,
                (thread_id, checkpoint_id),
            )
            row = cursor.fetchone()
            if not row or row["ts"] is None:
                cursor = conn.execute(
                    """
                    SELECT * FROM file_operations
                    WHERE thread_id = ? AND status = 'applied'
                    ORDER BY timestamp DESC
                    """,
                    (thread_id,),
                )
            else:
                target_ts = row["ts"]
                cursor = conn.execute(
                    """
                    SELECT * FROM file_operations
                    WHERE thread_id = ? AND timestamp >= ? AND status = 'applied'
                    ORDER BY timestamp DESC
                    """,
                    (thread_id, target_ts),
                )
            rows = cursor.fetchall()
        return [self._row_to_operation(row) for row in rows]

    def get_operations_between_checkpoints(
        self,
        thread_id: str,
        from_checkpoint_id: str,
        to_checkpoint_id: str,
    ) -> list[FileOperationRow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM file_operations
                WHERE thread_id = ?
                AND checkpoint_id != ?
                AND status = 'applied'
                ORDER BY timestamp DESC
                """,
                (thread_id, from_checkpoint_id),
            )
            rows = cursor.fetchall()

        result: list[FileOperationRow] = []
        found_target = False
        for row in rows:
            if row["checkpoint_id"] == to_checkpoint_id:
                found_target = True
            if found_target:
                break
            result.append(self._row_to_operation(row))
        return result

    def get_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM file_operations
                WHERE thread_id = ? AND checkpoint_id = ? AND status = 'applied'
                ORDER BY timestamp ASC
                """,
                (thread_id, checkpoint_id),
            )
            rows = cursor.fetchall()
        return [self._row_to_operation(row) for row in rows]

    def count_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM file_operations
                WHERE thread_id = ? AND checkpoint_id = ? AND status = 'applied'
                """,
                (thread_id, checkpoint_id),
            )
            return int(cursor.fetchone()[0])

    def mark_reverted(self, operation_ids: list[str]) -> None:
        if not operation_ids:
            return
        placeholders = ",".join("?" * len(operation_ids))
        with sqlite3.connect(self.db_path) as conn:
            # @@@param_sql - operation ids can originate from runtime state; keep IN-clause parameterized.
            conn.execute(
                f"""
                UPDATE file_operations
                SET status = 'reverted'
                WHERE id IN ({placeholders})
                """,
                operation_ids,
            )
            conn.commit()

    def delete_thread_operations(self, thread_id: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM file_operations WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()
            return int(cursor.rowcount)

    def _ensure_table(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_operations (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    operation_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    before_content TEXT,
                    after_content TEXT NOT NULL,
                    changes TEXT,
                    status TEXT DEFAULT 'applied'
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_ops_thread
                ON file_operations(thread_id, timestamp)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_file_ops_checkpoint
                ON file_operations(checkpoint_id)
                """
            )
            conn.commit()

    def _row_to_operation(self, row: sqlite3.Row) -> FileOperationRow:
        return FileOperationRow(
            id=row["id"],
            thread_id=row["thread_id"],
            checkpoint_id=row["checkpoint_id"],
            timestamp=row["timestamp"],
            operation_type=row["operation_type"],
            file_path=row["file_path"],
            before_content=row["before_content"],
            after_content=row["after_content"],
            changes=json.loads(row["changes"]) if row["changes"] else None,
            status=row["status"],
        )
