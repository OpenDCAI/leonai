from __future__ import annotations

import sqlite3

from sandbox.chat_session import ChatSessionManager


class _DummyProvider:
    pass


def test_chat_session_manager_drops_legacy_unique_thread_index(tmp_path) -> None:
    db_path = tmp_path / "sandbox.db"
    conn = sqlite3.connect(str(db_path))

    # Minimal legacy schema: has required columns + legacy UNIQUE(thread_id) index.
    conn.execute(
        """
        CREATE TABLE chat_sessions (
          chat_session_id TEXT PRIMARY KEY,
          thread_id TEXT NOT NULL,
          terminal_id TEXT NOT NULL,
          lease_id TEXT NOT NULL,
          runtime_id TEXT,
          status TEXT NOT NULL DEFAULT 'active',
          idle_ttl_sec INTEGER NOT NULL,
          max_duration_sec INTEGER NOT NULL,
          budget_json TEXT,
          started_at TIMESTAMP NOT NULL,
          last_active_at TIMESTAMP NOT NULL,
          ended_at TIMESTAMP,
          close_reason TEXT
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_sessions_thread_id ON chat_sessions(thread_id)")
    conn.commit()
    conn.close()

    # Construction runs _ensure_tables() which must drop the legacy unique(thread_id) index in-place.
    _ = ChatSessionManager(provider=_DummyProvider(), db_path=db_path)

    conn = sqlite3.connect(str(db_path))
    indexes = conn.execute("PRAGMA index_list(chat_sessions)").fetchall()
    index_names = {row[1] for row in indexes}  # (seq, name, unique, origin, partial)
    assert "uq_chat_sessions_thread_id" not in index_names
    conn.close()

