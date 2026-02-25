"""SQLite repository for summaries persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path


class SQLiteSummaryRepo:
    """Repository boundary for summaries table operations."""

    def __init__(self, db_path: Path, connect_fn: Callable[[Path], sqlite3.Connection]) -> None:
        self.db_path = db_path
        self._connect = connect_fn

    def ensure_tables(self) -> None:
        with self._connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    summary_id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    summary_text TEXT NOT NULL,
                    compact_up_to_index INTEGER NOT NULL,
                    compacted_at INTEGER NOT NULL,
                    is_split_turn BOOLEAN DEFAULT FALSE,
                    split_turn_prefix TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_summaries_thread_id
                ON summaries(thread_id, is_active, created_at DESC)
                """
            )
            conn.commit()

    def save_summary(
        self,
        summary_id: str,
        thread_id: str,
        summary_text: str,
        compact_up_to_index: int,
        compacted_at: int,
        is_split_turn: bool,
        split_turn_prefix: str | None,
        created_at: str,
    ) -> None:
        with self._connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE summaries
                SET is_active = FALSE
                WHERE thread_id = ? AND is_active = TRUE
                """,
                (thread_id,),
            )
            conn.execute(
                """
                INSERT INTO summaries (
                    summary_id, thread_id, summary_text,
                    compact_up_to_index, compacted_at,
                    is_split_turn, split_turn_prefix,
                    is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    thread_id,
                    summary_text,
                    compact_up_to_index,
                    compacted_at,
                    is_split_turn,
                    split_turn_prefix,
                    True,
                    created_at,
                ),
            )
            conn.commit()

    def get_latest_summary_row(self, thread_id: str) -> sqlite3.Row | None:
        with self._connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                """
                SELECT summary_id, thread_id, summary_text,
                       compact_up_to_index, compacted_at,
                       is_split_turn, split_turn_prefix,
                       is_active, created_at
                FROM summaries
                WHERE thread_id = ? AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (thread_id,),
            ).fetchone()

    def list_summaries(self, thread_id: str) -> list[dict[str, object]]:
        with self._connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT summary_id, thread_id,
                       compact_up_to_index, compacted_at,
                       is_split_turn, is_active, created_at
                FROM summaries
                WHERE thread_id = ?
                ORDER BY created_at DESC
                """,
                (thread_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_thread_summaries(self, thread_id: str) -> None:
        with self._connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM summaries WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()
