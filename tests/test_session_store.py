"""Tests for SessionStore ABC and SQLiteSessionStore."""

import tempfile
from pathlib import Path

import pytest

from sandbox.provider import SessionInfo
from sandbox.sqlite_store import SQLiteSessionStore


@pytest.fixture
def store(tmp_path):
    s = SQLiteSessionStore(db_path=tmp_path / "test.db")
    yield s
    s.close()


def _info(session_id="sess-1", provider="docker", status="running"):
    return SessionInfo(session_id=session_id, provider=provider, status=status)


class TestSQLiteSessionStore:
    def test_save_and_get(self, store):
        store.save("t1", _info(), context_id="ctx-1")
        row = store.get("t1")
        assert row is not None
        assert row["thread_id"] == "t1"
        assert row["session_id"] == "sess-1"
        assert row["provider"] == "docker"
        assert row["status"] == "running"
        assert row["context_id"] == "ctx-1"

    def test_get_missing(self, store):
        assert store.get("nonexistent") is None

    def test_get_all(self, store):
        store.save("t1", _info("s1"), context_id=None)
        store.save("t2", _info("s2"), context_id=None)
        rows = store.get_all()
        assert len(rows) == 2
        ids = {r["thread_id"] for r in rows}
        assert ids == {"t1", "t2"}

    def test_update_status(self, store):
        store.save("t1", _info(), context_id=None)
        store.update_status("t1", "paused")
        row = store.get("t1")
        assert row["status"] == "paused"

    def test_touch(self, store):
        store.save("t1", _info(), context_id=None)
        old = store.get("t1")["last_active"]
        import time; time.sleep(0.01)
        store.touch("t1")
        new = store.get("t1")["last_active"]
        assert new >= old

    def test_delete(self, store):
        store.save("t1", _info(), context_id=None)
        store.delete("t1")
        assert store.get("t1") is None

    def test_save_replaces(self, store):
        store.save("t1", _info("s1"), context_id=None)
        store.save("t1", _info("s2"), context_id="new-ctx")
        row = store.get("t1")
        assert row["session_id"] == "s2"
        assert row["context_id"] == "new-ctx"

    def test_e2b_snapshot_roundtrip(self, store):
        files = [
            {"file_path": "/home/user/a.py", "content": b"print('a')"},
            {"file_path": "/home/user/b.py", "content": b"print('b')"},
        ]
        store.save_e2b_snapshot("t1", files)
        loaded = store.load_e2b_snapshot("t1")
        assert len(loaded) == 2
        paths = {f["file_path"] for f in loaded}
        assert paths == {"/home/user/a.py", "/home/user/b.py"}

    def test_e2b_snapshot_empty(self, store):
        assert store.load_e2b_snapshot("t1") == []

    def test_close_idempotent(self, store):
        store.close()
        store.close()  # should not raise
