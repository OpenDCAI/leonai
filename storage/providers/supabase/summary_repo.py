"""Supabase repository for summaries persistence operations."""

from __future__ import annotations

from typing import Any


class SupabaseSummaryRepo:
    """Minimal summary repository backed by a Supabase client."""

    _TABLE = "summaries"

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase summary repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase summary repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def close(self) -> None:
        """Compatibility no-op with SQLiteSummaryRepo."""
        return None

    def ensure_tables(self) -> None:
        """Supabase schema is expected to be created via migrations."""
        return None

    def save_summary(
        self,
        summary_id: str,
        thread_id: str,
        summary_text: str,
        compact_up_to_index: int,
        compacted_at: int,
        is_split_turn: bool,
        split_turn_prefix: str | None,
        created_at: str,
    ) -> None:
        self._table().update({"is_active": False}).eq("thread_id", thread_id).eq("is_active", True).execute()
        response = self._table().insert(
            {
                "summary_id": summary_id,
                "thread_id": thread_id,
                "summary_text": summary_text,
                "compact_up_to_index": compact_up_to_index,
                "compacted_at": compacted_at,
                "is_split_turn": is_split_turn,
                "split_turn_prefix": split_turn_prefix,
                "is_active": True,
                "created_at": created_at,
            }
        ).execute()
        rows = self._rows(response, "save_summary")
        if not rows:
            raise RuntimeError(
                "Supabase summary repo expected inserted row payload for save_summary. "
                "Check table permissions and Supabase client settings."
            )
        inserted_summary_id = rows[0].get("summary_id")
        if inserted_summary_id is None:
            raise RuntimeError(
                "Supabase summary repo expected inserted row with non-null summary_id for save_summary. "
                "Check summaries table schema."
            )

    def get_latest_summary_row(self, thread_id: str) -> dict[str, Any] | None:
        query = self._table().select(
            "summary_id,thread_id,summary_text,compact_up_to_index,compacted_at,"
            "is_split_turn,split_turn_prefix,is_active,created_at"
        ).eq("thread_id", thread_id).eq("is_active", True)
        query = self._order(query, "created_at", desc=True, operation="get_latest_summary_row")
        query = self._limit(query, 1, "get_latest_summary_row")
        rows = self._rows(query.execute(), "get_latest_summary_row")
        if not rows:
            return None
        return self._row_to_latest_summary(rows[0], "get_latest_summary_row")

    def list_summaries(self, thread_id: str) -> list[dict[str, object]]:
        query = self._table().select(
            "summary_id,thread_id,compact_up_to_index,compacted_at,is_split_turn,is_active,created_at"
        ).eq("thread_id", thread_id)
        query = self._order(query, "created_at", desc=True, operation="list_summaries")
        rows = self._rows(query.execute(), "list_summaries")
        return [self._row_to_summary_listing(row, "list_summaries") for row in rows]

    def delete_thread_summaries(self, thread_id: str) -> None:
        self._table().delete().eq("thread_id", thread_id).execute()

    def _table(self) -> Any:
        return self._client.table(self._TABLE)

    def _rows(self, response: Any, operation: str) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            payload = response.get("data")
        else:
            payload = getattr(response, "data", None)
        if payload is None:
            raise RuntimeError(
                f"Supabase summary repo expected `.data` payload for {operation}. "
                "Check Supabase client compatibility."
            )
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Supabase summary repo expected list payload for {operation}, "
                f"got {type(payload).__name__}."
            )
        for row in payload:
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Supabase summary repo expected dict row payload for {operation}, "
                    f"got {type(row).__name__}."
                )
        return payload

    def _order(self, query: Any, column: str, *, desc: bool, operation: str) -> Any:
        if not hasattr(query, "order"):
            raise RuntimeError(
                f"Supabase summary repo expects query.order(column, desc=bool) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.order(column, desc=desc)

    def _limit(self, query: Any, value: int, operation: str) -> Any:
        if not hasattr(query, "limit"):
            raise RuntimeError(
                f"Supabase summary repo expects query.limit(value) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.limit(value)

    def _row_to_latest_summary(self, row: dict[str, Any], operation: str) -> dict[str, Any]:
        summary_id = self._required(row, "summary_id", operation)
        thread_id = self._required(row, "thread_id", operation)
        summary_text = self._required(row, "summary_text", operation)
        compact_up_to_index = self._required(row, "compact_up_to_index", operation)
        compacted_at = self._required(row, "compacted_at", operation)
        is_split_turn = self._required(row, "is_split_turn", operation)
        is_active = self._required(row, "is_active", operation)
        created_at = self._required(row, "created_at", operation)
        split_turn_prefix = row.get("split_turn_prefix")
        if split_turn_prefix is not None:
            split_turn_prefix = str(split_turn_prefix)

        return {
            "summary_id": str(summary_id),
            "thread_id": str(thread_id),
            "summary_text": str(summary_text),
            "compact_up_to_index": int(compact_up_to_index),
            "compacted_at": int(compacted_at),
            "is_split_turn": self._as_bool(is_split_turn, "is_split_turn", operation),
            "split_turn_prefix": split_turn_prefix,
            "is_active": self._as_bool(is_active, "is_active", operation),
            "created_at": str(created_at),
        }

    def _row_to_summary_listing(self, row: dict[str, Any], operation: str) -> dict[str, object]:
        summary_id = self._required(row, "summary_id", operation)
        thread_id = self._required(row, "thread_id", operation)
        compact_up_to_index = self._required(row, "compact_up_to_index", operation)
        compacted_at = self._required(row, "compacted_at", operation)
        is_split_turn = self._required(row, "is_split_turn", operation)
        is_active = self._required(row, "is_active", operation)
        created_at = self._required(row, "created_at", operation)

        return {
            "summary_id": str(summary_id),
            "thread_id": str(thread_id),
            "compact_up_to_index": int(compact_up_to_index),
            "compacted_at": int(compacted_at),
            # @@@bool-normalization - avoid silent truthiness bugs like bool("false") == True on malformed payloads.
            "is_split_turn": self._as_bool(is_split_turn, "is_split_turn", operation),
            "is_active": self._as_bool(is_active, "is_active", operation),
            "created_at": str(created_at),
        }

    def _required(self, row: dict[str, Any], field: str, operation: str) -> Any:
        value = row.get(field)
        if value is None:
            raise RuntimeError(
                f"Supabase summary repo expected non-null {field} in {operation} row. "
                "Check summaries table schema."
            )
        return value

    def _as_bool(self, value: Any, field: str, operation: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        raise RuntimeError(
            f"Supabase summary repo expected {field} to be bool (or 0/1 int) in {operation} row, "
            f"got {type(value).__name__}."
        )
