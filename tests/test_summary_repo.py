import pytest

from core.storage.supabase_summary_repo import SupabaseSummaryRepo


class _FakeSupabaseResponse:
    def __init__(self, data):
        self.data = data


class _FakeSupabaseQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict]]):
        self._table_name = table_name
        self._tables = tables
        self._filters: list[tuple[str, object]] = []
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

        if self._order_by is not None:
            column, desc = self._order_by
            matching_rows = sorted(matching_rows, key=lambda row: row.get(column), reverse=desc)

        if self._limit_value is not None:
            matching_rows = matching_rows[: self._limit_value]

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


def test_supabase_summary_repo_save_list_get_and_delete():
    tables: dict[str, list[dict]] = {"summaries": []}
    repo = SupabaseSummaryRepo(client=_FakeSupabaseClient(tables=tables))

    repo.ensure_tables()
    repo.save_summary(
        summary_id="s-1",
        thread_id="t-1",
        summary_text="first",
        compact_up_to_index=10,
        compacted_at=20,
        is_split_turn=False,
        split_turn_prefix=None,
        created_at="2025-01-01T00:00:00",
    )
    repo.save_summary(
        summary_id="s-2",
        thread_id="t-1",
        summary_text="second",
        compact_up_to_index=30,
        compacted_at=40,
        is_split_turn=True,
        split_turn_prefix="prefix",
        created_at="2025-01-01T00:01:00",
    )

    latest = repo.get_latest_summary_row("t-1")
    assert latest is not None
    assert latest["summary_id"] == "s-2"
    assert latest["summary_text"] == "second"
    assert latest["is_split_turn"] is True
    assert latest["split_turn_prefix"] == "prefix"
    assert latest["is_active"] is True

    listed = repo.list_summaries("t-1")
    assert [row["summary_id"] for row in listed] == ["s-2", "s-1"]

    active_count = sum(1 for row in tables["summaries"] if row["is_active"])
    assert active_count == 1

    repo.delete_thread_summaries("t-1")
    assert repo.list_summaries("t-1") == []
    assert repo.get_latest_summary_row("t-1") is None


def test_supabase_summary_repo_requires_compatible_client():
    with pytest.raises(RuntimeError, match="table\\(name\\)"):
        SupabaseSummaryRepo(client=object())
