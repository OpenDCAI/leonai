"""Supabase repository for run event persistence operations."""

from __future__ import annotations

import json
from typing import Any


class SupabaseRunEventRepo:
    """Minimal run event repository backed by a Supabase client."""

    _TABLE = "run_events"

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase run event repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase run event repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def close(self) -> None:
        """Compatibility no-op with SQLiteRunEventRepo."""
        return None

    def append_event(
        self,
        thread_id: str,
        run_id: str,
        event_type: str,
        data: dict[str, Any],
        message_id: str | None = None,
    ) -> int:
        response = self._table().insert(
            {
                "thread_id": thread_id,
                "run_id": run_id,
                "event_type": event_type,
                "data": json.dumps(data, ensure_ascii=False),
                "message_id": message_id,
            }
        ).execute()
        rows = self._rows(response, "append_event")
        if not rows:
            raise RuntimeError(
                "Supabase run event repo expected inserted row payload for append_event. "
                "Check table permissions and Supabase client settings."
            )
        seq = rows[0].get("seq")
        if seq is None:
            raise RuntimeError(
                "Supabase run event repo expected inserted row with non-null seq for append_event. "
                "Check run_events table schema."
            )
        return int(seq)

    def list_events(
        self,
        thread_id: str,
        run_id: str,
        *,
        after: int = 0,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        query = self._table().select("seq,event_type,data,message_id").eq("thread_id", thread_id).eq("run_id", run_id)
        query = self._gt(query, "seq", after, "list_events")
        query = self._order(query, "seq", desc=False, operation="list_events")
        query = self._limit(query, limit, "list_events")
        rows = self._rows(query.execute(), "list_events")

        events: list[dict[str, Any]] = []
        for row in rows:
            seq = row.get("seq")
            if seq is None:
                raise RuntimeError(
                    "Supabase run event repo expected non-null seq in list_events row. "
                    "Check run_events table schema."
                )
            payload = row.get("data")
            if payload in (None, ""):
                parsed_payload: dict[str, Any] = {}
            elif isinstance(payload, str):
                try:
                    loaded = json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        "Supabase run event repo expected valid JSON string payload in list_events. "
                        f"Decode error: {exc}."
                    ) from exc
                if not isinstance(loaded, dict):
                    raise RuntimeError(
                        "Supabase run event repo expected dict JSON payload in list_events row, "
                        f"got {type(loaded).__name__}."
                    )
                parsed_payload = loaded
            elif isinstance(payload, dict):
                parsed_payload = payload
            else:
                raise RuntimeError(
                    "Supabase run event repo expected string or dict payload in list_events row, "
                    f"got {type(payload).__name__}."
                )

            message_id = row.get("message_id")
            if message_id is not None and not isinstance(message_id, str):
                raise RuntimeError(
                    "Supabase run event repo expected message_id to be str or null in list_events row, "
                    f"got {type(message_id).__name__}."
                )

            events.append(
                {
                    "seq": int(seq),
                    "event_type": str(row.get("event_type") or ""),
                    "data": parsed_payload,
                    "message_id": message_id,
                }
            )
        return events

    def latest_seq(self, thread_id: str) -> int:
        query = self._table().select("seq").eq("thread_id", thread_id)
        query = self._order(query, "seq", desc=True, operation="latest_seq")
        query = self._limit(query, 1, "latest_seq")
        rows = self._rows(query.execute(), "latest_seq")
        if not rows:
            return 0
        seq = rows[0].get("seq")
        if seq is None:
            raise RuntimeError(
                "Supabase run event repo expected non-null seq in latest_seq row. "
                "Check run_events table schema."
            )
        return int(seq)

    def latest_run_id(self, thread_id: str) -> str | None:
        query = self._table().select("run_id,seq").eq("thread_id", thread_id)
        query = self._order(query, "seq", desc=True, operation="latest_run_id")
        query = self._limit(query, 1, "latest_run_id")
        rows = self._rows(query.execute(), "latest_run_id")
        if not rows:
            return None
        run_id = rows[0].get("run_id")
        return str(run_id) if run_id else None

    def list_run_ids(self, thread_id: str) -> list[str]:
        query = self._table().select("run_id,seq").eq("thread_id", thread_id)
        query = self._order(query, "seq", desc=True, operation="list_run_ids")
        rows = self._rows(query.execute(), "list_run_ids")

        run_ids: list[str] = []
        seen: set[str] = set()
        # @@@run-id-ordering - preserve SQLite ordering: latest sequence first, with duplicates removed by first sighting.
        for row in rows:
            run_id = row.get("run_id")
            if not run_id:
                continue
            run_id_value = str(run_id)
            if run_id_value in seen:
                continue
            seen.add(run_id_value)
            run_ids.append(run_id_value)
        return run_ids

    def delete_runs(self, thread_id: str, run_ids: list[str]) -> int:
        if not run_ids:
            return 0

        rows = self._rows(
            self._in_(self._table().select("seq").eq("thread_id", thread_id), "run_id", run_ids, "delete_runs").execute(),
            "delete_runs pre-count",
        )
        self._in_(self._table().delete().eq("thread_id", thread_id), "run_id", run_ids, "delete_runs").execute()
        return len(rows)

    def delete_thread_events(self, thread_id: str) -> int:
        rows = self._rows(self._table().select("seq").eq("thread_id", thread_id).execute(), "delete_thread_events pre-count")
        self._table().delete().eq("thread_id", thread_id).execute()
        return len(rows)

    def _table(self) -> Any:
        return self._client.table(self._TABLE)

    def _rows(self, response: Any, operation: str) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            payload = response.get("data")
        else:
            payload = getattr(response, "data", None)
        if payload is None:
            raise RuntimeError(
                f"Supabase run event repo expected `.data` payload for {operation}. "
                "Check Supabase client compatibility."
            )
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Supabase run event repo expected list payload for {operation}, "
                f"got {type(payload).__name__}."
            )
        for row in payload:
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Supabase run event repo expected dict row payload for {operation}, "
                    f"got {type(row).__name__}."
                )
        return payload

    def _in_(self, query: Any, column: str, values: list[str], operation: str) -> Any:
        if not hasattr(query, "in_"):
            raise RuntimeError(
                f"Supabase run event repo expects query.in_(column, values) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.in_(column, values)

    def _gt(self, query: Any, column: str, value: int, operation: str) -> Any:
        if not hasattr(query, "gt"):
            raise RuntimeError(
                f"Supabase run event repo expects query.gt(column, value) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.gt(column, value)

    def _order(self, query: Any, column: str, *, desc: bool, operation: str) -> Any:
        if not hasattr(query, "order"):
            raise RuntimeError(
                f"Supabase run event repo expects query.order(column, desc=bool) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.order(column, desc=desc)

    def _limit(self, query: Any, value: int, operation: str) -> Any:
        if not hasattr(query, "limit"):
            raise RuntimeError(
                f"Supabase run event repo expects query.limit(value) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.limit(value)
