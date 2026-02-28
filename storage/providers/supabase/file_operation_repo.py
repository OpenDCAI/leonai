"""Supabase repository for file operation persistence operations."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from storage.models import FileOperationRow
from storage.providers.supabase import _query


class SupabaseFileOperationRepo:
    """Minimal file operation repository backed by a Supabase client."""

    _TABLE = "file_operations"

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase file operation repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase file operation repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def close(self) -> None:
        """Compatibility no-op with SQLiteFileOperationRepo."""
        return None

    def record(
        self,
        thread_id: str,
        checkpoint_id: str,
        operation_type: str,
        file_path: str,
        before_content: str | None,
        after_content: str,
        changes: list[dict] | None = None,
    ) -> str:
        op_id = str(uuid.uuid4())
        response = self._table().insert(
            {
                "id": op_id,
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "timestamp": time.time(),
                "operation_type": operation_type,
                "file_path": file_path,
                "before_content": before_content,
                "after_content": after_content,
                "changes": changes,
                "status": "applied",
            }
        ).execute()
        rows = _query.rows(response, "record")
        if not rows:
            raise RuntimeError(
                "Supabase file operation repo expected inserted row payload for record. "
                "Check table permissions and Supabase client settings."
            )
        inserted_id = rows[0].get("id")
        if not inserted_id:
            raise RuntimeError(
                "Supabase file operation repo expected inserted row with non-null id for record. "
                "Check file_operations table schema."
            )
        return str(inserted_id)

    def get_operations_for_thread(self, thread_id: str, status: str = "applied") -> list[FileOperationRow]:
        query = self._table().select("*").eq("thread_id", thread_id).eq("status", status)
        query = _query.order(query, "timestamp", desc=False, operation="get_operations_for_thread")
        rows = _query.rows(query.execute(), "get_operations_for_thread")
        return [self._row_to_operation(row, "get_operations_for_thread") for row in rows]

    def get_operations_after_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        checkpoint_query = self._table().select("timestamp").eq("thread_id", thread_id).eq("checkpoint_id", checkpoint_id)
        checkpoint_query = _query.order(
            checkpoint_query,
            "timestamp",
            desc=False,
            operation="get_operations_after_checkpoint checkpoint timestamp",
        )
        checkpoint_query = _query.limit(checkpoint_query, 1, "get_operations_after_checkpoint checkpoint timestamp")
        checkpoint_rows = _query.rows(
            checkpoint_query.execute(),
            "get_operations_after_checkpoint checkpoint timestamp",
        )

        if not checkpoint_rows:
            query = self._table().select("*").eq("thread_id", thread_id).eq("status", "applied")
            query = _query.order(query, "timestamp", desc=True, operation="get_operations_after_checkpoint")
            rows = _query.rows(query.execute(), "get_operations_after_checkpoint")
            return [self._row_to_operation(row, "get_operations_after_checkpoint") for row in rows]

        target_ts = checkpoint_rows[0].get("timestamp")
        if target_ts is None:
            raise RuntimeError(
                "Supabase file operation repo expected non-null timestamp in checkpoint lookup row. "
                "Check file_operations table schema."
            )
        query = self._table().select("*").eq("thread_id", thread_id).eq("status", "applied")
        query = _query.gte(query, "timestamp", target_ts, "get_operations_after_checkpoint")
        query = _query.order(query, "timestamp", desc=True, operation="get_operations_after_checkpoint")
        rows = _query.rows(query.execute(), "get_operations_after_checkpoint")
        return [self._row_to_operation(row, "get_operations_after_checkpoint") for row in rows]

    def get_operations_between_checkpoints(
        self,
        thread_id: str,
        from_checkpoint_id: str,
        to_checkpoint_id: str,
    ) -> list[FileOperationRow]:
        query = self._table().select("*").eq("thread_id", thread_id).eq("status", "applied")
        query = _query.order(query, "timestamp", desc=True, operation="get_operations_between_checkpoints")
        rows = _query.rows(query.execute(), "get_operations_between_checkpoints")

        result: list[FileOperationRow] = []
        found_target = False
        for row in rows:
            checkpoint_id = row.get("checkpoint_id")
            if checkpoint_id == from_checkpoint_id:
                continue
            if checkpoint_id == to_checkpoint_id:
                found_target = True
            # @@@checkpoint-window-order - preserve SQLite loop behavior: stop once the target checkpoint is seen in descending timeline.
            if found_target:
                break
            result.append(self._row_to_operation(row, "get_operations_between_checkpoints"))
        return result

    def get_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> list[FileOperationRow]:
        query = self._table().select("*").eq("thread_id", thread_id).eq("checkpoint_id", checkpoint_id).eq("status", "applied")
        query = _query.order(query, "timestamp", desc=False, operation="get_operations_for_checkpoint")
        rows = _query.rows(query.execute(), "get_operations_for_checkpoint")
        return [self._row_to_operation(row, "get_operations_for_checkpoint") for row in rows]

    def count_operations_for_checkpoint(self, thread_id: str, checkpoint_id: str) -> int:
        query = self._table().select("id").eq("thread_id", thread_id).eq("checkpoint_id", checkpoint_id).eq("status", "applied")
        rows = _query.rows(query.execute(), "count_operations_for_checkpoint")
        return len(rows)

    def mark_reverted(self, operation_ids: list[str]) -> None:
        if not operation_ids:
            return
        query = _query.in_(
            self._table().update({"status": "reverted"}),
            "id",
            operation_ids,
            "mark_reverted",
        )
        query.execute()

    def delete_thread_operations(self, thread_id: str) -> int:
        rows = _query.rows(self._table().select("id").eq("thread_id", thread_id).execute(), "delete_thread_operations pre-count")
        self._table().delete().eq("thread_id", thread_id).execute()
        return len(rows)

    def _table(self) -> Any:
        return self._client.table(self._TABLE)



    def _row_to_operation(self, row: dict[str, Any], operation: str) -> FileOperationRow:
        op_id = row.get("id")
        thread_id = row.get("thread_id")
        checkpoint_id = row.get("checkpoint_id")
        timestamp = row.get("timestamp")
        operation_type = row.get("operation_type")
        file_path = row.get("file_path")
        after_content = row.get("after_content")
        status = row.get("status")

        required_fields = {
            "id": op_id,
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "timestamp": timestamp,
            "operation_type": operation_type,
            "file_path": file_path,
            "after_content": after_content,
            "status": status,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise RuntimeError(
                f"Supabase file operation repo expected non-null {', '.join(missing)} in {operation} row. "
                "Check file_operations table schema."
            )

        before_content = row.get("before_content")
        if before_content is not None and not isinstance(before_content, str):
            raise RuntimeError(
                "Supabase file operation repo expected before_content to be str or null, "
                f"got {type(before_content).__name__} in {operation} row."
            )

        changes_value = row.get("changes")
        if changes_value in (None, ""):
            changes: list[dict[str, Any]] | None = None
        elif isinstance(changes_value, str):
            try:
                loaded = json.loads(changes_value)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Supabase file operation repo expected valid JSON string payload in changes column. "
                    f"Decode error: {exc}."
                ) from exc
            if not isinstance(loaded, list):
                raise RuntimeError(
                    "Supabase file operation repo expected changes JSON payload to decode to list, "
                    f"got {type(loaded).__name__}."
                )
            if not all(isinstance(item, dict) for item in loaded):
                raise RuntimeError(
                    "Supabase file operation repo expected changes JSON payload items to be dict."
                )
            changes = loaded
        elif isinstance(changes_value, list):
            if not all(isinstance(item, dict) for item in changes_value):
                raise RuntimeError(
                    "Supabase file operation repo expected changes list payload items to be dict."
                )
            changes = changes_value
        else:
            raise RuntimeError(
                "Supabase file operation repo expected changes to be list, JSON string, or null, "
                f"got {type(changes_value).__name__} in {operation} row."
            )

        return FileOperationRow(
            id=str(op_id),
            thread_id=str(thread_id),
            checkpoint_id=str(checkpoint_id),
            timestamp=float(timestamp),
            operation_type=str(operation_type),
            file_path=str(file_path),
            before_content=before_content,
            after_content=str(after_content),
            changes=changes,
            status=str(status),
        )
