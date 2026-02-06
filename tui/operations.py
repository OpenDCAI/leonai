"""File operation recorder for time travel functionality"""

import json
import sqlite3
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

# Context variables for tracking current thread and checkpoint
current_thread_id: ContextVar[str] = ContextVar("current_thread_id", default="")
current_checkpoint_id: ContextVar[str] = ContextVar("current_checkpoint_id", default="")


@dataclass
class FileOperation:
    """Represents a single file operation"""

    id: str
    thread_id: str
    checkpoint_id: str
    timestamp: float
    operation_type: str  # 'write', 'edit', 'multi_edit'
    file_path: str
    before_content: str | None
    after_content: str
    changes: list[dict] | None  # For edit operations: [{old_string, new_string}]
    status: str = "applied"  # 'applied', 'reverted'


class FileOperationRecorder:
    """Records file operations for time travel rollback"""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            db_path = Path.home() / ".leon" / "leon.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the file_operations table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
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
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_ops_thread
                ON file_operations(thread_id, timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_ops_checkpoint
                ON file_operations(checkpoint_id)
            """)
            conn.commit()

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
        """Record a file operation"""
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

    def get_operations_for_thread(self, thread_id: str, status: str = "applied") -> list[FileOperation]:
        """Get all operations for a thread"""
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

    def get_operations_after_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperation]:
        """Get operations after a specific checkpoint (for rollback)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # First get the timestamp of the target checkpoint
            cursor = conn.execute(
                """
                SELECT MIN(timestamp) as ts FROM file_operations
                WHERE thread_id = ? AND checkpoint_id = ?
                """,
                (thread_id, checkpoint_id),
            )
            row = cursor.fetchone()
            if not row or row["ts"] is None:
                # No operations for this checkpoint, get all after it
                # We need to find operations with checkpoint_id > target
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
        self, thread_id: str, from_checkpoint_id: str, to_checkpoint_id: str
    ) -> list[FileOperation]:
        """Get operations between two checkpoints (exclusive of from, inclusive of to)"""
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
            # Filter to only include operations after from_checkpoint
            result = []
            found_target = False
            for row in rows:
                if row["checkpoint_id"] == to_checkpoint_id:
                    found_target = True
                if found_target:
                    break
                result.append(self._row_to_operation(row))
            return result

    def get_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperation]:
        """Get all operations for a specific checkpoint"""
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
        """Count operations for a specific checkpoint"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM file_operations
                WHERE thread_id = ? AND checkpoint_id = ? AND status = 'applied'
                """,
                (thread_id, checkpoint_id),
            )
            return cursor.fetchone()[0]

    def mark_reverted(self, operation_ids: list[str]) -> None:
        """Mark operations as reverted"""
        if not operation_ids:
            return
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ",".join("?" * len(operation_ids))
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
        """Delete all operations for a thread"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM file_operations WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()
            return cursor.rowcount

    def _row_to_operation(self, row: sqlite3.Row) -> FileOperation:
        """Convert a database row to FileOperation"""
        return FileOperation(
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


# Global recorder instance (initialized lazily)
_recorder: FileOperationRecorder | None = None


def get_recorder() -> FileOperationRecorder:
    """Get or create the global recorder instance"""
    global _recorder
    if _recorder is None:
        _recorder = FileOperationRecorder()
    return _recorder


def set_recorder(recorder: FileOperationRecorder) -> None:
    """Set the global recorder instance"""
    global _recorder
    _recorder = recorder
