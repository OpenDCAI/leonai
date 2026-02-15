"""SummaryStore - Persistent storage for conversation summaries.

This module implements persistent storage for MemoryMiddleware summaries,
preventing loss of cached summaries across restarts.

Architecture:
    MemoryMiddleware → SummaryStore → SQLite
    - Summaries stored with thread_id as key
    - Only latest summary per thread is active
    - Historical summaries retained for audit
"""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sandbox.db import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def _connect(db_path: Path) -> sqlite3.Connection:
    """Create SQLite connection with proper timeout settings."""
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@dataclass
class SummaryData:
    """Summary data snapshot.

    Represents a conversation summary that persists across sessions.
    """

    summary_id: str
    thread_id: str
    summary_text: str
    compact_up_to_index: int
    compacted_at: int
    is_split_turn: bool = False
    split_turn_prefix: str | None = None
    is_active: bool = True
    created_at: str | None = None


class SummaryStore:
    """Store for managing conversation summary persistence.

    Handles CRUD operations for summaries in the database.
    Follows the same pattern as TerminalStore for consistency.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """Ensure summaries table exists."""
        with _connect(self.db_path) as conn:
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
            # Index for fast lookup by thread_id
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_summaries_thread_id
                ON summaries(thread_id, is_active, created_at DESC)
                """
            )
            conn.commit()

    def save_summary(
        self,
        thread_id: str,
        summary_text: str,
        compact_up_to_index: int,
        compacted_at: int,
        is_split_turn: bool = False,
        split_turn_prefix: str | None = None,
        max_retries: int = 3,
    ) -> str:
        """Save a new summary and mark old summaries as inactive.

        Args:
            thread_id: Thread identifier
            summary_text: The summary content
            compact_up_to_index: Index up to which messages were compacted
            compacted_at: Total message count when compaction occurred
            is_split_turn: Whether this is a split turn summary
            split_turn_prefix: Optional prefix summary for split turns
            max_retries: Maximum number of retry attempts on failure

        Returns:
            summary_id: The generated summary ID

        Raises:
            sqlite3.Error: If save fails after all retries
        """
        summary_id = f"{thread_id}_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        for attempt in range(max_retries):
            try:
                with _connect(self.db_path) as conn:
                    # Mark all existing summaries for this thread as inactive
                    conn.execute(
                        """
                        UPDATE summaries
                        SET is_active = FALSE
                        WHERE thread_id = ? AND is_active = TRUE
                        """,
                        (thread_id,),
                    )

                    # Insert new summary
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
                            now,
                        ),
                    )
                    conn.commit()

                logger.info(f"[SummaryStore] Saved summary {summary_id} for thread {thread_id}")
                return summary_id

            except sqlite3.Error as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[SummaryStore] Save failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"[SummaryStore] Save failed after {max_retries} attempts: {e}")
                    raise

    def get_latest_summary(
        self,
        thread_id: str,
        max_retries: int = 3,
    ) -> SummaryData | None:
        """Get the latest active summary for a thread.

        Args:
            thread_id: Thread identifier
            max_retries: Maximum number of retry attempts on failure

        Returns:
            SummaryData if found, None if no summary exists or data is corrupted
        """
        for attempt in range(max_retries):
            try:
                with _connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    row = conn.execute(
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

                    if not row:
                        return None

                    # Validate data integrity
                    try:
                        return SummaryData(
                            summary_id=row["summary_id"],
                            thread_id=row["thread_id"],
                            summary_text=row["summary_text"],
                            compact_up_to_index=row["compact_up_to_index"],
                            compacted_at=row["compacted_at"],
                            is_split_turn=bool(row["is_split_turn"]),
                            split_turn_prefix=row["split_turn_prefix"],
                            is_active=bool(row["is_active"]),
                            created_at=row["created_at"],
                        )
                    except (KeyError, TypeError, ValueError) as e:
                        logger.error(f"[SummaryStore] Data corruption detected: {e}")
                        return None  # Signal data corruption

            except sqlite3.Error as e:
                if attempt < max_retries - 1:
                    logger.warning(f"[SummaryStore] Read failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"[SummaryStore] Read failed after {max_retries} attempts: {e}")
                    return None  # Signal failure

        return None

    def list_summaries(self, thread_id: str) -> list[dict[str, Any]]:
        """List all summaries for a thread (for audit purposes).

        Args:
            thread_id: Thread identifier

        Returns:
            List of summary records as dictionaries
        """
        with _connect(self.db_path) as conn:
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
        """Delete all summaries for a thread.

        Args:
            thread_id: Thread identifier
        """
        with _connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM summaries WHERE thread_id = ?",
                (thread_id,),
            )
            conn.commit()

        logger.info(f"[SummaryStore] Deleted all summaries for thread {thread_id}")
