"""Supabase repository for thread-level config persistence operations."""

from __future__ import annotations

from typing import Any

from storage.providers.supabase import _query as q

_REPO = "thread config repo"
_TABLE = "thread_config"


class SupabaseThreadConfigRepo:
    """Minimal thread config repository backed by a Supabase client."""

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
        return None

    def save_metadata(self, thread_id: str, sandbox_type: str, cwd: str | None) -> None:
        if self.lookup_metadata(thread_id) is None:
            self._t().insert({"thread_id": thread_id, "sandbox_type": sandbox_type, "cwd": cwd}).execute()
            return
        self._t().update({"sandbox_type": sandbox_type, "cwd": cwd}).eq("thread_id", thread_id).execute()

    def save_model(self, thread_id: str, model: str) -> None:
        # @@@model-update-contract - match SQLite behavior: update only model on existing rows.
        if self.lookup_metadata(thread_id) is None:
            self._t().insert({"thread_id": thread_id, "sandbox_type": "local", "model": model}).execute()
            return
        self._t().update({"model": model}).eq("thread_id", thread_id).execute()

    def update_fields(self, thread_id: str, **fields: str | None) -> None:
        allowed = {"sandbox_type", "cwd", "model", "queue_mode", "observation_provider"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if updates:
            self._t().update(updates).eq("thread_id", thread_id).execute()

    def lookup_model(self, thread_id: str) -> str | None:
        rows = self._select(thread_id, "model")
        if not rows:
            return None
        model = rows[0].get("model")
        return str(model) if model else None

    def lookup_config(self, thread_id: str) -> dict[str, str | None] | None:
        rows = self._select(thread_id, "sandbox_type,cwd,model,queue_mode,observation_provider")
        if not rows:
            return None
        sandbox_type = rows[0].get("sandbox_type")
        if sandbox_type is None:
            raise RuntimeError(
                "Supabase thread config repo expected non-null sandbox_type. "
                "Check table schema and existing rows."
            )
        return {
            "sandbox_type": str(sandbox_type),
            "cwd": str(rows[0]["cwd"]) if rows[0].get("cwd") is not None else None,
            "model": str(rows[0]["model"]) if rows[0].get("model") is not None else None,
            "queue_mode": str(rows[0]["queue_mode"]) if rows[0].get("queue_mode") is not None else None,
            "observation_provider": str(rows[0]["observation_provider"]) if rows[0].get("observation_provider") is not None else None,
        }

    def lookup_metadata(self, thread_id: str) -> tuple[str, str | None] | None:
        rows = self._select(thread_id, "sandbox_type,cwd")
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

    def _t(self) -> Any:
        return self._client.table(_TABLE)

    def _select(self, thread_id: str, columns: str) -> list[dict[str, Any]]:
        return q.rows(self._t().select(columns).eq("thread_id", thread_id).execute(), _REPO, "select")
