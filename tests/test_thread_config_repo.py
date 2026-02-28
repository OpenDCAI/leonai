import sqlite3
from pathlib import Path

import pytest

from backend.web.utils import helpers
from storage.providers.sqlite.thread_config_repo import SQLiteThreadConfigRepo
from storage.providers.supabase.thread_config_repo import SupabaseThreadConfigRepo


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
        repo.update_fields("t-2", queue_mode="followup", observation_provider="langfuse")
        cfg = repo.lookup_config("t-2")
        assert cfg is not None
        assert cfg["queue_mode"] == "followup"
        assert cfg["observation_provider"] == "langfuse"
    finally:
        repo.close()


def test_helpers_compatibility_api(tmp_path, monkeypatch):
    db_path = tmp_path / "leon.db"
    monkeypatch.setattr(helpers, "DB_PATH", Path(db_path))

    helpers.init_thread_config("t-3", "local", "/tmp/p")
    helpers.save_thread_model("t-3", "m-3")

    config = helpers.load_thread_config("t-3")
    assert config is not None
    assert (config.sandbox_type, config.cwd) == ("local", "/tmp/p")
    assert helpers.lookup_thread_model("t-3") == "m-3"
    helpers.save_thread_config("t-3", queue_mode="followup", observation_provider="langsmith")
    config2 = helpers.load_thread_config("t-3")
    assert config2 is not None
    assert config2.queue_mode == "followup"
    assert config2.observation_provider == "langsmith"


class _FakeSupabaseResponse:
    def __init__(self, data):
        self.data = data


class _FakeSupabaseQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict]]):
        self._table_name = table_name
        self._tables = tables
        self._filters: list[tuple[str, object]] = []
        self._insert_payload: dict | None = None
        self._update_payload: dict | None = None

    def select(self, _: str):
        return self

    def eq(self, column: str, value):
        self._filters.append((column, value))
        return self

    def insert(self, payload: dict):
        self._insert_payload = dict(payload)
        return self

    def update(self, payload: dict):
        self._update_payload = dict(payload)
        return self

    def execute(self):
        table = self._tables.setdefault(self._table_name, [])

        if self._insert_payload is not None:
            row = dict(self._insert_payload)
            table.append(row)
            return _FakeSupabaseResponse([row])

        matching_rows = list(table)
        for column, value in self._filters:
            matching_rows = [row for row in matching_rows if row.get(column) == value]

        if self._update_payload is not None:
            updated_rows: list[dict] = []
            for row in table:
                include = True
                for column, value in self._filters:
                    if row.get(column) != value:
                        include = False
                        break
                if include:
                    row.update(self._update_payload)
                    updated_rows.append(dict(row))
            return _FakeSupabaseResponse(updated_rows)

        return _FakeSupabaseResponse([dict(row) for row in matching_rows])


class _FakeSupabaseClient:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = tables

    def table(self, table_name: str):
        return _FakeSupabaseQuery(table_name, self._tables)


def test_supabase_thread_config_repo_save_and_lookup():
    tables: dict[str, list[dict]] = {"thread_config": []}
    repo = SupabaseThreadConfigRepo(client=_FakeSupabaseClient(tables=tables))

    repo.save_metadata("t-1", "docker", "/workspace")
    repo.save_model("t-1", "anthropic/claude-sonnet-4.6")

    assert repo.lookup_metadata("t-1") == ("docker", "/workspace")
    assert repo.lookup_model("t-1") == "anthropic/claude-sonnet-4.6"

    repo.save_model("t-2", "openai/gpt-5")
    assert repo.lookup_metadata("t-2") == ("local", None)
    assert repo.lookup_model("t-2") == "openai/gpt-5"
    repo.update_fields("t-1", queue_mode="followup", observation_provider="langfuse")
    cfg = repo.lookup_config("t-1")
    assert cfg is not None
    assert cfg["queue_mode"] == "followup"
    assert cfg["observation_provider"] == "langfuse"


def test_supabase_thread_config_repo_requires_compatible_client():
    with pytest.raises(RuntimeError, match="table\\(name\\)"):
        SupabaseThreadConfigRepo(client=object())
