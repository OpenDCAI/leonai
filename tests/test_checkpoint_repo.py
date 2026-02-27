import sqlite3
from pathlib import Path

import pytest

from core.memory.checkpoint_repo import SQLiteCheckpointRepo
from core.storage.providers.supabase.checkpoint_repo import SupabaseCheckpointRepo


def _setup_tables(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE writes (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE checkpoint_writes (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE checkpoint_blobs (thread_id TEXT, checkpoint_id TEXT)")
        conn.commit()


def test_list_thread_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-2", "c1"))
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-1", "c2"))
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-1", "c3"))
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        assert repo.list_thread_ids() == ["t-1", "t-2"]
    finally:
        repo.close()


def test_delete_checkpoints_by_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_blobs (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        repo.delete_checkpoints_by_ids("t-1", ["c2", "c3"])
    finally:
        repo.close()

    with sqlite3.connect(str(db_path)) as conn:
        left_checkpoints = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoints ORDER BY thread_id, checkpoint_id"
        ).fetchall()
        left_writes = conn.execute("SELECT thread_id, checkpoint_id FROM writes ORDER BY thread_id, checkpoint_id").fetchall()
        left_cp_writes = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoint_writes ORDER BY thread_id, checkpoint_id"
        ).fetchall()
        left_cp_blobs = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoint_blobs ORDER BY thread_id, checkpoint_id"
        ).fetchall()

    assert left_checkpoints == [("t-1", "c1"), ("t-2", "c2")]
    assert left_writes == [("t-2", "c2")]
    assert left_cp_writes == [("t-2", "c2")]
    assert left_cp_blobs == [("t-2", "c2")]


def test_delete_thread_data(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_blobs (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        repo.delete_thread_data("t-1")
    finally:
        repo.close()

    with sqlite3.connect(str(db_path)) as conn:
        left_checkpoints = conn.execute("SELECT thread_id FROM checkpoints ORDER BY thread_id").fetchall()
        left_writes = conn.execute("SELECT thread_id FROM writes ORDER BY thread_id").fetchall()
        left_cp_writes = conn.execute("SELECT thread_id FROM checkpoint_writes ORDER BY thread_id").fetchall()
        left_cp_blobs = conn.execute("SELECT thread_id FROM checkpoint_blobs ORDER BY thread_id").fetchall()

    assert left_checkpoints == [("t-2",)]
    assert left_writes == [("t-2",)]
    assert left_cp_writes == [("t-2",)]
    assert left_cp_blobs == [("t-2",)]


class _FakeSupabaseResponse:
    def __init__(self, data):
        self.data = data


class _FakeSupabaseQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict]]):
        self._table_name = table_name
        self._tables = tables
        self._filters: list[tuple[str, object]] = []
        self._in_filter: tuple[str, list[object]] | None = None
        self._delete_requested = False

    def select(self, _: str):
        return self

    def delete(self):
        self._delete_requested = True
        return self

    def eq(self, column: str, value):
        self._filters.append((column, value))
        return self

    def in_(self, column: str, values: list[object]):
        self._in_filter = (column, list(values))
        return self

    def execute(self):
        rows = list(self._tables.get(self._table_name, []))
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        if self._in_filter is not None:
            column, values = self._in_filter
            rows = [row for row in rows if row.get(column) in values]
        if self._delete_requested:
            self._tables[self._table_name] = [
                row for row in self._tables.get(self._table_name, []) if row not in rows
            ]
            return _FakeSupabaseResponse([])
        return _FakeSupabaseResponse(rows)


class _FakeSupabaseClient:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables

    def table(self, table_name: str):
        return _FakeSupabaseQuery(table_name, self.tables)


def test_supabase_checkpoint_repo_list_and_delete():
    tables = {
        "checkpoints": [
            {"thread_id": "t-2", "checkpoint_id": "c1"},
            {"thread_id": "t-1", "checkpoint_id": "c2"},
            {"thread_id": "t-1", "checkpoint_id": "c3"},
        ],
        "writes": [
            {"thread_id": "t-1", "checkpoint_id": "c2"},
            {"thread_id": "t-1", "checkpoint_id": "c3"},
            {"thread_id": "t-2", "checkpoint_id": "c2"},
        ],
        "checkpoint_writes": [
            {"thread_id": "t-1", "checkpoint_id": "c2"},
            {"thread_id": "t-1", "checkpoint_id": "c3"},
            {"thread_id": "t-2", "checkpoint_id": "c2"},
        ],
        "checkpoint_blobs": [
            {"thread_id": "t-1", "checkpoint_id": "c2"},
            {"thread_id": "t-1", "checkpoint_id": "c3"},
            {"thread_id": "t-2", "checkpoint_id": "c2"},
        ],
    }
    repo = SupabaseCheckpointRepo(client=_FakeSupabaseClient(tables=tables))
    assert repo.list_thread_ids() == ["t-1", "t-2"]

    repo.delete_checkpoints_by_ids("t-1", ["c2", "c3"])
    assert tables["checkpoints"] == [{"thread_id": "t-2", "checkpoint_id": "c1"}]
    assert tables["writes"] == [{"thread_id": "t-2", "checkpoint_id": "c2"}]
    assert tables["checkpoint_writes"] == [{"thread_id": "t-2", "checkpoint_id": "c2"}]
    assert tables["checkpoint_blobs"] == [{"thread_id": "t-2", "checkpoint_id": "c2"}]

    repo.delete_thread_data("t-2")
    assert tables["checkpoints"] == []
    assert tables["writes"] == []
    assert tables["checkpoint_writes"] == []
    assert tables["checkpoint_blobs"] == []


def test_supabase_checkpoint_repo_requires_compatible_client():
    with pytest.raises(RuntimeError, match="table\\(name\\)"):
        SupabaseCheckpointRepo(client=object())
