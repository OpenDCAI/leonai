from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from services.web.data_platform import sandbox_views


def _seed_min_sandbox_db(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE abstract_terminals (
          terminal_id TEXT PRIMARY KEY,
          thread_id TEXT NOT NULL,
          lease_id TEXT NOT NULL,
          cwd TEXT NOT NULL,
          env_delta_json TEXT DEFAULT '{}',
          state_version INTEGER DEFAULT 0,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE sandbox_leases (
          lease_id TEXT PRIMARY KEY,
          provider_name TEXT NOT NULL,
          workspace_key TEXT,
          current_instance_id TEXT,
          instance_created_at TIMESTAMP,
          desired_state TEXT NOT NULL DEFAULT 'running',
          observed_state TEXT NOT NULL DEFAULT 'running',
          version INTEGER NOT NULL DEFAULT 0,
          observed_at TIMESTAMP,
          last_error TEXT,
          needs_refresh INTEGER NOT NULL DEFAULT 0,
          refresh_hint_at TIMESTAMP,
          status TEXT DEFAULT 'active',
          created_at TIMESTAMP NOT NULL,
          updated_at TIMESTAMP NOT NULL
        )
        """
    )
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
    conn.execute(
        """
        CREATE TABLE thread_terminal_pointers (
          thread_id TEXT PRIMARY KEY,
          active_terminal_id TEXT NOT NULL,
          default_terminal_id TEXT NOT NULL,
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE terminal_commands (
          command_id TEXT PRIMARY KEY,
          terminal_id TEXT NOT NULL,
          chat_session_id TEXT,
          command_line TEXT NOT NULL,
          cwd TEXT NOT NULL,
          status TEXT NOT NULL,
          stdout TEXT DEFAULT '',
          stderr TEXT DEFAULT '',
          exit_code INTEGER,
          created_at TIMESTAMP NOT NULL,
          updated_at TIMESTAMP NOT NULL,
          finished_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO sandbox_leases (lease_id, provider_name, desired_state, observed_state, version, needs_refresh, status, created_at, updated_at)
        VALUES ('lease-1', 'local', 'running', 'running', 0, 0, 'active', '2026-02-15T00:00:00', '2026-02-15T00:00:00')
        """
    )
    conn.execute(
        """
        INSERT INTO abstract_terminals (terminal_id, thread_id, lease_id, cwd)
        VALUES ('term-1', 'thread-1', 'lease-1', '/tmp')
        """
    )
    conn.execute(
        """
        INSERT INTO chat_sessions (chat_session_id, thread_id, terminal_id, lease_id, status, idle_ttl_sec, max_duration_sec, started_at, last_active_at)
        VALUES ('sess-1', 'thread-1', 'term-1', 'lease-1', 'active', 60, 3600, '2026-02-15T00:00:00', '2026-02-15T00:00:01')
        """
    )
    conn.execute(
        """
        INSERT INTO thread_terminal_pointers (thread_id, active_terminal_id, default_terminal_id, updated_at)
        VALUES ('thread-1', 'term-1', 'term-1', '2026-02-15T00:00:01')
        """
    )
    conn.execute(
        """
        INSERT INTO terminal_commands (command_id, terminal_id, chat_session_id, command_line, cwd, status, created_at, updated_at)
        VALUES ('cmd-1', 'term-1', 'sess-1', 'echo hi', '/tmp', 'finished', '2026-02-15T00:00:02', '2026-02-15T00:00:02')
        """
    )
    conn.commit()
    conn.close()


def test_sandbox_views_roundtrip(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "sandbox.db"
    _seed_min_sandbox_db(db_path)
    monkeypatch.setenv("LEON_SANDBOX_DB_PATH", str(db_path))

    sessions = sandbox_views.list_active_sessions(limit=10)
    assert len(sessions) == 1
    assert sessions[0]["thread_id"] == "thread-1"
    assert sessions[0]["provider_name"] == "local"
    assert sessions[0]["last_command"]["command_id"] == "cmd-1"

    cmds = sandbox_views.list_thread_commands(thread_id="thread-1", limit=10)
    assert len(cmds) == 1
    assert cmds[0]["command_id"] == "cmd-1"

