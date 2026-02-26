"""Supabase repository for eval trajectory persistence operations."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from eval.models import RunTrajectory


class SupabaseEvalRepo:
    """Minimal eval repository backed by a Supabase client."""

    def __init__(self, client: Any) -> None:
        if client is None:
            raise RuntimeError(
                "Supabase eval repo requires a client. "
                "Pass supabase_client=... into StorageContainer(strategy='supabase')."
            )
        if not hasattr(client, "table"):
            raise RuntimeError(
                "Supabase eval repo requires a client with table(name). "
                "Use supabase-py client or a compatible adapter."
            )
        self._client = client

    def ensure_schema(self) -> None:
        """Supabase schema is expected to be created via migrations."""
        return None

    def save_trajectory(self, trajectory: RunTrajectory, trajectory_json: str) -> str:
        run_id = trajectory.id
        run_rows = self._rows(
            self._table("eval_runs").insert(
                {
                    "id": run_id,
                    "thread_id": trajectory.thread_id,
                    "started_at": trajectory.started_at,
                    "finished_at": trajectory.finished_at,
                    "user_message": trajectory.user_message,
                    "final_response": trajectory.final_response,
                    "status": trajectory.status,
                    "run_tree_json": trajectory.run_tree_json,
                    "trajectory_json": trajectory_json,
                }
            ).execute(),
            "save_trajectory eval_runs insert",
        )
        if not run_rows:
            raise RuntimeError(
                "Supabase eval repo expected inserted row payload for save_trajectory. "
                "Check table permissions and Supabase client settings."
            )

        for call in trajectory.llm_calls:
            rows = self._rows(
                self._table("eval_llm_calls").insert(
                    {
                        "id": str(uuid4()),
                        "run_id": run_id,
                        "parent_run_id": call.parent_run_id,
                        "duration_ms": call.duration_ms,
                        "input_tokens": call.input_tokens,
                        "output_tokens": call.output_tokens,
                        "total_tokens": call.total_tokens,
                        "cost_usd": call.cost_usd,
                        "model_name": call.model_name,
                    }
                ).execute(),
                "save_trajectory eval_llm_calls insert",
            )
            if not rows:
                raise RuntimeError(
                    "Supabase eval repo expected inserted row payload for eval_llm_calls in save_trajectory. "
                    "Check table permissions and Supabase client settings."
                )

        for call in trajectory.tool_calls:
            rows = self._rows(
                self._table("eval_tool_calls").insert(
                    {
                        "id": str(uuid4()),
                        "run_id": run_id,
                        "parent_run_id": call.parent_run_id,
                        "tool_name": call.tool_name,
                        "tool_call_id": call.tool_call_id,
                        "duration_ms": call.duration_ms,
                        "success": call.success,
                        "error": call.error,
                        "args_summary": call.args_summary,
                        "result_summary": call.result_summary,
                    }
                ).execute(),
                "save_trajectory eval_tool_calls insert",
            )
            if not rows:
                raise RuntimeError(
                    "Supabase eval repo expected inserted row payload for eval_tool_calls in save_trajectory. "
                    "Check table permissions and Supabase client settings."
                )
        return run_id

    def save_metrics(self, run_id: str, tier: str, timestamp: str, metrics_json: str) -> None:
        rows = self._rows(
            self._table("eval_metrics").insert(
                {
                    "id": str(uuid4()),
                    "run_id": run_id,
                    "tier": tier,
                    "timestamp": timestamp,
                    "metrics_json": metrics_json,
                }
            ).execute(),
            "save_metrics",
        )
        if not rows:
            raise RuntimeError(
                "Supabase eval repo expected inserted row payload for save_metrics. "
                "Check table permissions and Supabase client settings."
            )

    def get_trajectory_json(self, run_id: str) -> str | None:
        query = self._table("eval_runs").select("trajectory_json").eq("id", run_id)
        query = self._limit(query, 1, "get_trajectory_json")
        rows = self._rows(query.execute(), "get_trajectory_json")
        if not rows:
            return None
        trajectory_json = rows[0].get("trajectory_json")
        if trajectory_json is None:
            raise RuntimeError(
                "Supabase eval repo expected non-null trajectory_json in get_trajectory_json row. "
                "Check eval_runs table schema."
            )
        return str(trajectory_json)

    def list_runs(self, thread_id: str | None = None, limit: int = 50) -> list[dict]:
        query = self._table("eval_runs").select(
            "id,thread_id,started_at,finished_at,status,user_message"
        )
        if thread_id:
            query = query.eq("thread_id", thread_id)
        # @@@eval-list-order - match SQLite path by returning newest started_at first.
        query = self._order(query, "started_at", desc=True, operation="list_runs")
        query = self._limit(query, limit, "list_runs")
        rows = self._rows(query.execute(), "list_runs")
        result: list[dict] = []
        for row in rows:
            result.append(
                {
                    "id": str(row.get("id") or ""),
                    "thread_id": str(row.get("thread_id") or ""),
                    "started_at": row.get("started_at"),
                    "finished_at": row.get("finished_at"),
                    "status": str(row.get("status") or ""),
                    "user_message": str(row.get("user_message") or ""),
                }
            )
        return result

    def get_metrics(self, run_id: str, tier: str | None = None) -> list[dict]:
        query = self._table("eval_metrics").select("id,tier,timestamp,metrics_json").eq("run_id", run_id)
        if tier:
            query = query.eq("tier", tier)
        rows = self._rows(query.execute(), "get_metrics")
        result: list[dict] = []
        for row in rows:
            result.append(
                {
                    "id": str(row.get("id") or ""),
                    "tier": str(row.get("tier") or ""),
                    "timestamp": row.get("timestamp"),
                    "metrics_json": row.get("metrics_json"),
                }
            )
        return result

    def _table(self, table_name: str) -> Any:
        return self._client.table(table_name)

    def _rows(self, response: Any, operation: str) -> list[dict[str, Any]]:
        if isinstance(response, dict):
            payload = response.get("data")
        else:
            payload = getattr(response, "data", None)
        if payload is None:
            raise RuntimeError(
                f"Supabase eval repo expected `.data` payload for {operation}. "
                "Check Supabase client compatibility."
            )
        if not isinstance(payload, list):
            raise RuntimeError(
                f"Supabase eval repo expected list payload for {operation}, "
                f"got {type(payload).__name__}."
            )
        for row in payload:
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Supabase eval repo expected dict row payload for {operation}, "
                    f"got {type(row).__name__}."
                )
        return payload

    def _order(self, query: Any, column: str, *, desc: bool, operation: str) -> Any:
        if not hasattr(query, "order"):
            raise RuntimeError(
                f"Supabase eval repo expects query.order(column, desc=bool) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.order(column, desc=desc)

    def _limit(self, query: Any, value: int, operation: str) -> Any:
        if not hasattr(query, "limit"):
            raise RuntimeError(
                f"Supabase eval repo expects query.limit(value) support for {operation}. "
                "Provide a supabase-py compatible query object."
            )
        return query.limit(value)
