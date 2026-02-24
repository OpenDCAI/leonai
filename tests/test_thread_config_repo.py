import sqlite3
from pathlib import Path

from backend.web.utils import helpers
from core.memory.thread_config_repo import SQLiteThreadConfigRepo


def test_migrate_thread_metadata_table(tmp_path):
    db_path = tmp_path / "leon.db"
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE thread_metadata (thread_id TEXT PRIMARY KEY, sandbox_type TEXT NOT NULL, cwd TEXT, model TEXT)"
        )
        conn.execute(
            "INSERT INTO thread_metadata (thread_id, sandbox_type, cwd, model) VALUES (?, ?, ?, ?)",
            ("t-1", "local", "/tmp/ws", "m-1"),
        )
        conn.commit()

    repo = SQLiteThreadConfigRepo(db_path)
    try:
        assert repo.lookup_metadata("t-1") == ("local", "/tmp/ws")
        assert repo.lookup_model("t-1") == "m-1"
    finally:
        repo.close()

    with sqlite3.connect(str(db_path)) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "thread_config" in tables
        assert "thread_metadata" not in tables


def test_save_and_lookup_thread_config(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteThreadConfigRepo(db_path)
    try:
        repo.save_metadata("t-2", "docker", "/workspace")
        repo.save_model("t-2", "anthropic/claude-sonnet-4.6")
        assert repo.lookup_metadata("t-2") == ("docker", "/workspace")
        assert repo.lookup_model("t-2") == "anthropic/claude-sonnet-4.6"
    finally:
        repo.close()


def test_helpers_compatibility_api(tmp_path, monkeypatch):
    db_path = tmp_path / "leon.db"
    monkeypatch.setattr(helpers, "DB_PATH", Path(db_path))

    helpers.save_thread_metadata("t-3", "local", "/tmp/p")
    helpers.save_thread_model("t-3", "m-3")

    assert helpers.lookup_thread_metadata("t-3") == ("local", "/tmp/p")
    assert helpers.lookup_thread_model("t-3") == "m-3"
