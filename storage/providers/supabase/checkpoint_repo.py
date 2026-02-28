"""Supabase repository for checkpoint/writes persistence operations."""

from __future__ import annotations

from typing import Any
from storage.providers.supabase import _query


class SupabaseCheckpointRepo:
    """Minimal checkpoint repository backed by a Supabase client."""

    _TABLES = ("checkpoints", "writes", "checkpoint_writes", "checkpoint_blobs")

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase checkpoint repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase checkpoint repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def close(self) -> None:
        """Compatibility no-op with SQLiteCheckpointRepo."""
        return None

    def list_thread_ids(self) -> list[str]:
        response = self._table("checkpoints").select("thread_id").execute()
        rows = _query.rows(response, "list_thread_ids")
        return sorted({str(row["thread_id"]) for row in rows if row.get("thread_id")})

    def delete_thread_data(self, thread_id: str) -> None:
        for table in self._TABLES:
            self._table(table).delete().eq("thread_id", thread_id).execute()

    def delete_checkpoints_by_ids(self, thread_id: str, checkpoint_ids: list[str]) -> None:
        if not checkpoint_ids:
            return

        for table in self._TABLES:
            query = self._table(table).delete().eq("thread_id", thread_id)
            if not hasattr(query, "in_"):
                raise RuntimeError(
                    "Supabase checkpoint repo expects query.in_(column, values) support. "
                    "Provide a supabase-py compatible query object."
                )
            # @@@supabase-in-clause - checkpoint IDs are external input, keep values in explicit list for PostgREST in_.
            query.in_("checkpoint_id", checkpoint_ids).execute()

    def _table(self, table_name: str) -> Any:
        return self._client.table(table_name)

