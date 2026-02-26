"""Supabase repository for thread-level config persistence operations."""

from __future__ import annotations

from typing import Any


class SupabaseThreadConfigRepo:
    """Minimal thread config repository backed by a Supabase client."""

    _TABLE = "thread_config"

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase thread config repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase thread config repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def close(self) -> None:
        """Compatibility no-op with SQLiteThreadConfigRepo."""
        return None

    def save_metadata(self, thread_id: str, sandbox_type: str, cwd: str | None) -> None:
        if self.lookup_metadata(thread_id) is None:
            self._table().insert(
                {
                    "thread_id": thread_id,
                    "sandbox_type": sandbox_type,
                    "cwd": cwd,
                }
            ).execute()
            return

        self._table().update(
            {
                "sandbox_type": sandbox_type,
                "cwd": cwd,
            }
        ).eq("thread_id", thread_id).execute()

    def save_model(self, thread_id: str, model: str) -> None:
        # @@@model-update-contract - match SQLite behavior: update only model on existing rows, default sandbox_type for first insert.
        if self.lookup_metadata(thread_id) is None:
            self._table().insert(
                {
                    "thread_id": thread_id,
                    "sandbox_type": "local",
                    "model": model,
                }
            ).execute()
            return

        self._table().update({"model": model}).eq("thread_id", thread_id).execute()

    def lookup_model(self, thread_id: str) -> str | None:
        rows = self._select_rows(thread_id, "model")
        if not rows:
            return None
        model = rows[0].get("model")
        return str(model) if model else None

    def lookup_metadata(self, thread_id: str) -> tuple[str, str | None] | None:
        rows = self._select_rows(thread_id, "sandbox_type,cwd")
        if not rows:
            return None

        sandbox_type = rows[0].get("sandbox_type")
        if sandbox_type is None:
            raise RuntimeError(
                "Supabase thread config repo expected non-null sandbox_type. "
                "Check table schema and existing rows."
            )
        cwd = rows[0].get("cwd")
        return str(sandbox_type), str(cwd) if cwd is not None else None

    def _select_rows(self, thread_id: str, columns: str) -> list[dict[str, Any]]:
        response = self._table().select(columns).eq("thread_id", thread_id).execute()
        return self._rows(response, "select thread config")

    def _table(self) -> Any:
        return self._client.table(self._TABLE)

    def _rows(self, response: Any, operation: str) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            payload = response.get("data")
        else:
            payload = getattr(response, "data", None)
        if payload is None:
            raise RuntimeError(
                f"Supabase thread config repo expected `.data` payload for {operation}. "
                "Check Supabase client compatibility."
            )
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Supabase thread config repo expected list payload for {operation}, "
                f"got {type(payload).__name__}."
            )
        for row in payload:
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Supabase thread config repo expected dict row payload for {operation}, "
                    f"got {type(row).__name__}."
                )
        return payload
