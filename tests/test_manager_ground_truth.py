"""Tests for SandboxManager inspect ground-truth behavior."""

import asyncio
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sandbox.manager import SandboxManager
from sandbox.provider import Metrics, ProviderExecResult, SandboxProvider, SessionInfo


class FakeProvider(SandboxProvider):
    name = "fake"

    def __init__(self):
        self._statuses: dict[str, str] = {}

    def create_session(self, context_id: str | None = None) -> SessionInfo:
        sid = f"s-{uuid.uuid4().hex[:8]}"
        self._statuses[sid] = "running"
        return SessionInfo(session_id=sid, provider=self.name, status="running")

    def destroy_session(self, session_id: str, sync: bool = True) -> bool:
        self._statuses.pop(session_id, None)
        return True

    def pause_session(self, session_id: str) -> bool:
        if session_id in self._statuses:
            self._statuses[session_id] = "paused"
            return True
        return False

    def resume_session(self, session_id: str) -> bool:
        if session_id in self._statuses:
            self._statuses[session_id] = "running"
            return True
        return False

    def get_session_status(self, session_id: str) -> str:
        return self._statuses.get(session_id, "deleted")

    def execute(
        self,
        session_id: str,
        command: str,
        timeout_ms: int = 30000,
        cwd: str | None = None,
    ) -> ProviderExecResult:
        return ProviderExecResult(output="", exit_code=0, error=None)

    def read_file(self, session_id: str, path: str) -> str:
        return ""

    def write_file(self, session_id: str, path: str, content: str) -> str:
        return "ok"

    def list_dir(self, session_id: str, path: str) -> list[dict]:
        return []

    def get_metrics(self, session_id: str) -> Metrics | None:
        return None

    def list_provider_sessions(self) -> list[SessionInfo]:
        return [
            SessionInfo(session_id=sid, provider=self.name, status=status) for sid, status in self._statuses.items()
        ]


def _temp_db() -> Path:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


def test_list_sessions_shows_running_lease_without_chat_session() -> None:
    db = _temp_db()
    try:
        provider = FakeProvider()
        mgr = SandboxManager(provider=provider, db_path=db)
        lease = mgr.lease_store.create("lease-1", provider.name)
        instance = lease.ensure_active_instance(provider)
        mgr.terminal_store.create("term-1", "thread-1", "lease-1", "/home/user")

        rows = mgr.list_sessions()
        assert rows
        row = rows[0]
        assert row["thread_id"] == "thread-1"
        assert row["instance_id"] == instance.instance_id
        assert row["status"] == "running"
        assert row["source"] == "lease"
    finally:
        db.unlink(missing_ok=True)


def test_list_sessions_includes_provider_orphan() -> None:
    db = _temp_db()
    try:
        provider = FakeProvider()
        mgr = SandboxManager(provider=provider, db_path=db)
        orphan = provider.create_session()
        rows = mgr.list_sessions()
        assert any(r["instance_id"] == orphan.session_id and r["source"] == "provider_orphan" for r in rows)
    finally:
        db.unlink(missing_ok=True)


def test_enforce_idle_timeouts_pauses_lease_and_closes_session() -> None:
    db = _temp_db()
    try:
        provider = FakeProvider()
        mgr = SandboxManager(provider=provider, db_path=db)

        capability = mgr.get_sandbox("thread-1")
        asyncio.run(capability.command.execute("echo hi"))
        session_id = capability._session.session_id
        instance_id = capability._session.lease.get_instance().instance_id

        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                """
                UPDATE chat_sessions
                SET idle_ttl_sec = 1, last_active_at = ?
                WHERE chat_session_id = ?
                """,
                ((datetime.now() - timedelta(seconds=5)).isoformat(), session_id),
            )
            conn.commit()

        count = mgr.enforce_idle_timeouts()
        assert count == 1
        assert provider.get_session_status(instance_id) == "paused"
        assert mgr.session_manager.get("thread-1") is None
    finally:
        db.unlink(missing_ok=True)
