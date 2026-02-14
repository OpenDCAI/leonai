from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.web.data_platform.api import create_operator_router
from services.web.data_platform.store import create_run, ensure_tables, insert_event


class _DummyRuntime:
    def get_status_dict(self):
        return {"state": "active", "note": "dummy"}


class _DummyAgent:
    runtime = _DummyRuntime()


class _DummyLock:
    def __init__(self, locked: bool):
        self._locked = locked

    def locked(self) -> bool:
        return self._locked


class _DummyTask:
    def done(self) -> bool:
        return False

    def cancelled(self) -> bool:
        return False


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
          desired_state TEXT NOT NULL DEFAULT 'running',
          observed_state TEXT NOT NULL DEFAULT 'running',
          version INTEGER NOT NULL DEFAULT 0,
          needs_refresh INTEGER NOT NULL DEFAULT 0,
          status TEXT DEFAULT 'active',
          created_at TIMESTAMP NOT NULL,
          updated_at TIMESTAMP NOT NULL,
          last_error TEXT
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
          status TEXT NOT NULL DEFAULT 'active',
          idle_ttl_sec INTEGER NOT NULL,
          max_duration_sec INTEGER NOT NULL,
          started_at TIMESTAMP NOT NULL,
          last_active_at TIMESTAMP NOT NULL
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
        VALUES ('term-1', 't1', 'lease-1', '/tmp')
        """
    )
    conn.execute(
        """
        INSERT INTO chat_sessions (chat_session_id, thread_id, terminal_id, lease_id, status, idle_ttl_sec, max_duration_sec, started_at, last_active_at)
        VALUES ('sess-1', 't1', 'term-1', 'lease-1', 'active', 60, 3600, '2026-02-15T00:00:00', '2026-02-15T00:00:01')
        """
    )
    conn.execute(
        """
        INSERT INTO thread_terminal_pointers (thread_id, active_terminal_id, default_terminal_id, updated_at)
        VALUES ('t1', 'term-1', 'term-1', '2026-02-15T00:00:01')
        """
    )
    conn.execute(
        """
        INSERT INTO terminal_commands (command_id, terminal_id, chat_session_id, command_line, cwd, status, created_at, updated_at, finished_at, exit_code)
        VALUES ('cmd-1', 'term-1', 'sess-1', 'echo hi', '/tmp', 'finished', '2026-02-15T00:00:02', '2026-02-15T00:00:02', '2026-02-15T00:00:02', 0)
        """
    )
    conn.commit()
    conn.close()


def test_operator_thread_diagnostics_reports_state(monkeypatch) -> None:
    with TemporaryDirectory() as td:
        dp_db_path = Path(td) / "dp.db"
        ensure_tables(dp_db_path)
        run_id = create_run(db_path=dp_db_path, thread_id="t1", sandbox="local", input_message="hello")
        insert_event(db_path=dp_db_path, run_id=run_id, thread_id="t1", event_type="run", payload={"run_id": run_id})

        sandbox_db_path = Path(td) / "sandbox.db"
        _seed_min_sandbox_db(sandbox_db_path)
        monkeypatch.setenv("LEON_SANDBOX_DB_PATH", str(sandbox_db_path))

        app = FastAPI()
        app.state.agent_pool = {"t1:local": _DummyAgent()}
        app.state.thread_locks = {"t1": _DummyLock(True)}
        app.state.thread_tasks = {"t1": _DummyTask()}

        app.include_router(create_operator_router(dp_db_path=dp_db_path))

        with TestClient(app) as client:
            resp = client.get("/api/operator/threads/t1/diagnostics")
            assert resp.status_code == 200
            body = resp.json()
            assert body["thread_id"] == "t1"
            assert body["data_platform"]["latest_run"]["run_id"] == run_id
            assert body["data_platform"]["latest_run_last_event_id"] >= 1
            assert body["runtime"]["state"] == "active"
            assert body["in_memory"]["thread_lock_locked"] is True
            assert body["sandbox_db"]["active_sessions"][0]["thread_id"] == "t1"
            assert body["sandbox_db"]["commands"][0]["command_id"] == "cmd-1"

