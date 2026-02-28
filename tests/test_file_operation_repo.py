from storage.providers.sqlite.file_operation_repo import SQLiteFileOperationRepo
import pytest

from storage.providers.supabase.file_operation_repo import SupabaseFileOperationRepo


def test_record_and_query_file_operations(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteFileOperationRepo(db_path)

    op1 = repo.record("t-1", "cp-1", "write", "/tmp/a.txt", None, "hello")
    op2 = repo.record("t-1", "cp-2", "edit", "/tmp/a.txt", "hello", "world", [{"old": "hello", "new": "world"}])

    assert op1 != op2

    rows = repo.get_operations_for_thread("t-1")
    assert len(rows) == 2
    assert rows[0].checkpoint_id == "cp-1"
    assert rows[1].changes == [{"old": "hello", "new": "world"}]


def test_mark_reverted_and_status_filter(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteFileOperationRepo(db_path)

    op1 = repo.record("t-2", "cp-1", "write", "/tmp/a.txt", None, "a")
    repo.record("t-2", "cp-1", "write", "/tmp/b.txt", None, "b")

    repo.mark_reverted([op1])

    applied = repo.get_operations_for_thread("t-2", status="applied")
    reverted = repo.get_operations_for_thread("t-2", status="reverted")

    assert len(applied) == 1
    assert len(reverted) == 1
    assert reverted[0].id == op1


def test_delete_thread_operations(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteFileOperationRepo(db_path)

    repo.record("t-3", "cp-1", "write", "/tmp/a.txt", None, "a")
    repo.record("t-3", "cp-2", "write", "/tmp/b.txt", None, "b")
    repo.record("t-x", "cp-x", "write", "/tmp/c.txt", None, "c")

    deleted = repo.delete_thread_operations("t-3")
    assert deleted == 2
    assert repo.get_operations_for_thread("t-3") == []
    assert len(repo.get_operations_for_thread("t-x")) == 1


class _FakeSupabaseResponse:
    def __init__(self, data):
        self.data = data


class _FakeSupabaseQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict]]):
        self._table_name = table_name
        self._tables = tables
        self._filters: list[tuple[str, object]] = []
        self._in_filter: tuple[str, list[object]] | None = None
        self._gte_filter: tuple[str, object] | None = None
        self._order_by: tuple[str, bool] | None = None
        self._limit_value: int | None = None
        self._insert_payload: dict | None = None
        self._update_payload: dict | None = None
        self._delete_requested = False

    def select(self, _: str):
        return self

    def insert(self, payload: dict):
        self._insert_payload = dict(payload)
        return self

    def update(self, payload: dict):
        self._update_payload = dict(payload)
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

    def gte(self, column: str, value):
        self._gte_filter = (column, value)
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
            row = dict(self._insert_payload)
            table.append(row)
            return _FakeSupabaseResponse([dict(row)])

        matching_rows = list(table)
        for column, value in self._filters:
            matching_rows = [row for row in matching_rows if row.get(column) == value]

        if self._in_filter is not None:
            column, values = self._in_filter
            matching_rows = [row for row in matching_rows if row.get(column) in values]

        if self._gte_filter is not None:
            column, value = self._gte_filter
            matching_rows = [row for row in matching_rows if row.get(column) >= value]

        if self._order_by is not None:
            column, desc = self._order_by
            matching_rows = sorted(matching_rows, key=lambda row: row.get(column), reverse=desc)

        if self._limit_value is not None:
            matching_rows = matching_rows[: self._limit_value]

        if self._update_payload is not None:
            updated_rows: list[dict] = []
            for row in table:
                if row in matching_rows:
                    row.update(self._update_payload)
                    updated_rows.append(dict(row))
            return _FakeSupabaseResponse(updated_rows)

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


def test_supabase_file_operation_repo_record_and_query():
    tables: dict[str, list[dict]] = {"file_operations": []}
    repo = SupabaseFileOperationRepo(client=_FakeSupabaseClient(tables=tables))

    op1 = repo.record("t-1", "cp-1", "write", "/tmp/a.txt", None, "hello")
    op2 = repo.record("t-1", "cp-2", "edit", "/tmp/a.txt", "hello", "world", [{"old": "hello", "new": "world"}])

    rows = repo.get_operations_for_thread("t-1")
    assert [row.id for row in rows] == [op1, op2]
    assert rows[1].changes == [{"old": "hello", "new": "world"}]

    for_checkpoint = repo.get_operations_for_checkpoint("t-1", "cp-2")
    assert len(for_checkpoint) == 1
    assert for_checkpoint[0].id == op2
    assert repo.count_operations_for_checkpoint("t-1", "cp-2") == 1

    after_cp2 = repo.get_operations_after_checkpoint("t-1", "cp-2")
    assert [row.id for row in after_cp2] == [op2]


def test_supabase_file_operation_repo_mark_reverted_and_delete_thread():
    tables: dict[str, list[dict]] = {"file_operations": []}
    repo = SupabaseFileOperationRepo(client=_FakeSupabaseClient(tables=tables))

    op1 = repo.record("t-2", "cp-1", "write", "/tmp/a.txt", None, "a")
    repo.record("t-2", "cp-1", "write", "/tmp/b.txt", None, "b")
    repo.record("t-x", "cp-x", "write", "/tmp/c.txt", None, "c")

    repo.mark_reverted([op1])

    applied = repo.get_operations_for_thread("t-2", status="applied")
    reverted = repo.get_operations_for_thread("t-2", status="reverted")
    assert len(applied) == 1
    assert len(reverted) == 1
    assert reverted[0].id == op1

    deleted = repo.delete_thread_operations("t-2")
    assert deleted == 2
    assert repo.get_operations_for_thread("t-2") == []
    assert len(repo.get_operations_for_thread("t-x")) == 1


def test_supabase_file_operation_repo_requires_compatible_client():
    with pytest.raises(RuntimeError, match="table\\(name\\)"):
        SupabaseFileOperationRepo(client=object())
