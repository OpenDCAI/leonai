import sqlite3

import pytest

from core.memory.run_event_repo import SQLiteRunEventRepo
from core.storage.supabase_run_event_repo import SupabaseRunEventRepo


def test_append_and_list_events_with_cursor(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        seq1 = repo.append_event("t-1", "r-1", "tool_call", {"name": "ls"}, "m-1")
        seq2 = repo.append_event("t-1", "r-1", "tool_result", {"ok": True}, "m-2")

        assert seq1 == 1
        assert seq2 == 2

        events = repo.list_events("t-1", "r-1", after=0)
        assert [event["event_type"] for event in events] == ["tool_call", "tool_result"]

        cursor_events = repo.list_events("t-1", "r-1", after=1)
        assert len(cursor_events) == 1
        assert cursor_events[0]["seq"] == 2
        assert cursor_events[0]["data"] == {"ok": True}
    finally:
        repo.close()


def test_latest_and_list_run_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        repo.append_event("t-2", "r-1", "status", {"s": 1})
        repo.append_event("t-2", "r-2", "status", {"s": 2})
        repo.append_event("t-2", "r-1", "status", {"s": 3})

        assert repo.latest_seq("t-2") == 3
        assert repo.latest_run_id("t-2") == "r-1"
        assert repo.list_run_ids("t-2") == ["r-1", "r-2"]
    finally:
        repo.close()


def test_delete_runs_and_thread_events(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        repo.append_event("t-3", "r-1", "status", {"v": 1})
        repo.append_event("t-3", "r-2", "status", {"v": 2})
        repo.append_event("t-3", "r-2", "status", {"v": 3})

        deleted = repo.delete_runs("t-3", ["r-2"])
        assert deleted == 2
        assert repo.list_run_ids("t-3") == ["r-1"]

        deleted_all = repo.delete_thread_events("t-3")
        assert deleted_all == 1
        assert repo.latest_seq("t-3") == 0

        with sqlite3.connect(str(db_path)) as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM run_events WHERE thread_id = ?", ("t-3",)).fetchone()[0]
            assert remaining == 0
    finally:
        repo.close()


class _FakeSupabaseResponse:
    def __init__(self, data):
        self.data = data


class _FakeSupabaseQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict]]):
        self._table_name = table_name
        self._tables = tables
        self._filters: list[tuple[str, object]] = []
        self._in_filter: tuple[str, list[object]] | None = None
        self._gt_filter: tuple[str, object] | None = None
        self._order_by: tuple[str, bool] | None = None
        self._limit_value: int | None = None
        self._insert_payload: dict | None = None
        self._delete_requested = False

    def select(self, _: str):
        return self

    def insert(self, payload: dict):
        self._insert_payload = dict(payload)
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

    def gt(self, column: str, value):
        self._gt_filter = (column, value)
        return self

    def order(self, column: str, desc: bool = False):
        self._order_by = (column, desc)
        return self

    def limit(self, value: int):
        self._limit_value = value
        return self

    def execute(self):
        table = self._tables.setdefault(self._table_name, [])

        if self._insert_payload is not None:
            next_seq = 1 + max((int(row.get("seq", 0)) for row in table), default=0)
            row = dict(self._insert_payload)
            row["seq"] = next_seq
            table.append(row)
            return _FakeSupabaseResponse([dict(row)])

        matching_rows = list(table)
        for column, value in self._filters:
            matching_rows = [row for row in matching_rows if row.get(column) == value]

        if self._in_filter is not None:
            column, values = self._in_filter
            matching_rows = [row for row in matching_rows if row.get(column) in values]

        if self._gt_filter is not None:
            column, value = self._gt_filter
            matching_rows = [row for row in matching_rows if row.get(column) > value]

        if self._order_by is not None:
            column, desc = self._order_by
            matching_rows = sorted(matching_rows, key=lambda row: row.get(column), reverse=desc)

        if self._limit_value is not None:
            matching_rows = matching_rows[: self._limit_value]

        if self._delete_requested:
            self._tables[self._table_name] = [
                row for row in self._tables.get(self._table_name, []) if row not in matching_rows
            ]
            return _FakeSupabaseResponse([dict(row) for row in matching_rows])

        return _FakeSupabaseResponse([dict(row) for row in matching_rows])


class _FakeSupabaseClient:
    def __init__(self, tables: dict[str, list[dict]]):
        self._tables = tables

    def table(self, table_name: str):
        return _FakeSupabaseQuery(table_name, self._tables)


def test_supabase_run_event_repo_append_and_list_events_with_cursor():
    tables: dict[str, list[dict]] = {"run_events": []}
    repo = SupabaseRunEventRepo(client=_FakeSupabaseClient(tables=tables))

    seq1 = repo.append_event("t-1", "r-1", "tool_call", {"name": "ls"}, "m-1")
    seq2 = repo.append_event("t-1", "r-1", "tool_result", {"ok": True}, "m-2")

    assert seq1 == 1
    assert seq2 == 2

    events = repo.list_events("t-1", "r-1", after=0)
    assert [event["event_type"] for event in events] == ["tool_call", "tool_result"]

    cursor_events = repo.list_events("t-1", "r-1", after=1)
    assert len(cursor_events) == 1
    assert cursor_events[0]["seq"] == 2
    assert cursor_events[0]["data"] == {"ok": True}


def test_supabase_run_event_repo_latest_and_list_run_ids():
    tables: dict[str, list[dict]] = {"run_events": []}
    repo = SupabaseRunEventRepo(client=_FakeSupabaseClient(tables=tables))

    repo.append_event("t-2", "r-1", "status", {"s": 1})
    repo.append_event("t-2", "r-2", "status", {"s": 2})
    repo.append_event("t-2", "r-1", "status", {"s": 3})

    assert repo.latest_seq("t-2") == 3
    assert repo.latest_run_id("t-2") == "r-1"
    assert repo.list_run_ids("t-2") == ["r-1", "r-2"]


def test_supabase_run_event_repo_delete_runs_and_thread_events():
    tables: dict[str, list[dict]] = {"run_events": []}
    repo = SupabaseRunEventRepo(client=_FakeSupabaseClient(tables=tables))

    repo.append_event("t-3", "r-1", "status", {"v": 1})
    repo.append_event("t-3", "r-2", "status", {"v": 2})
    repo.append_event("t-3", "r-2", "status", {"v": 3})

    deleted = repo.delete_runs("t-3", ["r-2"])
    assert deleted == 2
    assert repo.list_run_ids("t-3") == ["r-1"]

    deleted_all = repo.delete_thread_events("t-3")
    assert deleted_all == 1
    assert repo.latest_seq("t-3") == 0
    assert tables["run_events"] == []


def test_supabase_run_event_repo_requires_compatible_client():
    with pytest.raises(RuntimeError, match="table\\(name\\)"):
        SupabaseRunEventRepo(client=object())
