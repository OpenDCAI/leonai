"""SQLite storage for eval trajectories and metrics.

Database: ~/.leon/eval.db (separate from main leon.db)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC
from pathlib import Path
from uuid import uuid4

from eval.models import (
    ObjectiveMetrics,
    RunTrajectory,
    SystemMetrics,
)

_DEFAULT_DB_PATH = Path.home() / ".leon" / "eval.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS eval_runs (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    user_message TEXT,
    final_response TEXT,
    status TEXT DEFAULT 'completed',
    run_tree_json TEXT,
    trajectory_json TEXT
);

CREATE TABLE IF NOT EXISTS eval_llm_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    parent_run_id TEXT,
    duration_ms REAL DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd REAL DEFAULT 0,
    model_name TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES eval_runs(id)
);

CREATE TABLE IF NOT EXISTS eval_tool_calls (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    parent_run_id TEXT,
    tool_name TEXT NOT NULL,
    tool_call_id TEXT DEFAULT '',
    duration_ms REAL DEFAULT 0,
    success INTEGER DEFAULT 1,
    error TEXT,
    args_summary TEXT DEFAULT '',
    result_summary TEXT DEFAULT '',
    FOREIGN KEY (run_id) REFERENCES eval_runs(id)
);

CREATE TABLE IF NOT EXISTS eval_metrics (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    timestamp TEXT,
    metrics_json TEXT,
    FOREIGN KEY (run_id) REFERENCES eval_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_thread ON eval_runs(thread_id, started_at);
CREATE INDEX IF NOT EXISTS idx_eval_tool_name ON eval_tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS idx_eval_metrics_run ON eval_metrics(run_id, tier);
"""


class TrajectoryStore:
    """SQLite-backed storage for eval trajectories and metrics."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def save_trajectory(self, trajectory: RunTrajectory) -> str:
        """Save a trajectory and its LLM/tool call records. Returns run_id."""
        run_id = trajectory.id
        trajectory_json = trajectory.model_dump_json()

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO eval_runs (id, thread_id, started_at, finished_at, "
                "user_message, final_response, status, run_tree_json, trajectory_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    trajectory.thread_id,
                    trajectory.started_at,
                    trajectory.finished_at,
                    trajectory.user_message,
                    trajectory.final_response,
                    trajectory.status,
                    trajectory.run_tree_json,
                    trajectory_json,
                ),
            )

            for call in trajectory.llm_calls:
                conn.execute(
                    "INSERT INTO eval_llm_calls (id, run_id, parent_run_id, "
                    "duration_ms, input_tokens, output_tokens, total_tokens, "
                    "cost_usd, model_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        run_id,
                        call.parent_run_id,
                        call.duration_ms,
                        call.input_tokens,
                        call.output_tokens,
                        call.total_tokens,
                        call.cost_usd,
                        call.model_name,
                    ),
                )

            for call in trajectory.tool_calls:
                conn.execute(
                    "INSERT INTO eval_tool_calls (id, run_id, parent_run_id, "
                    "tool_name, tool_call_id, duration_ms, success, error, "
                    "args_summary, result_summary) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(uuid4()),
                        run_id,
                        call.parent_run_id,
                        call.tool_name,
                        call.tool_call_id,
                        call.duration_ms,
                        int(call.success),
                        call.error,
                        call.args_summary,
                        call.result_summary,
                    ),
                )

        return run_id

    def save_metrics(
        self,
        run_id: str,
        tier: str,
        metrics: SystemMetrics | ObjectiveMetrics,
    ) -> None:
        """Save computed metrics for a run."""
        from datetime import datetime

        with self._connect() as conn:
            conn.execute(
                "INSERT INTO eval_metrics (id, run_id, tier, timestamp, metrics_json) VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    run_id,
                    tier,
                    datetime.now(UTC).isoformat(),
                    metrics.model_dump_json(),
                ),
            )

    def get_trajectory(self, run_id: str) -> RunTrajectory | None:
        """Load a trajectory by run_id."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT trajectory_json FROM eval_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
            if not row or not row["trajectory_json"]:
                return None
            return RunTrajectory.model_validate_json(row["trajectory_json"])

    def list_runs(self, thread_id: str | None = None, limit: int = 50) -> list[dict]:
        """List eval runs, optionally filtered by thread_id."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if thread_id:
                rows = conn.execute(
                    "SELECT id, thread_id, started_at, finished_at, status, "
                    "user_message FROM eval_runs "
                    "WHERE thread_id = ? ORDER BY started_at DESC LIMIT ?",
                    (thread_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, thread_id, started_at, finished_at, status, "
                    "user_message FROM eval_runs "
                    "ORDER BY started_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def get_metrics(self, run_id: str, tier: str | None = None) -> list[dict]:
        """Get metrics for a run, optionally filtered by tier."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if tier:
                rows = conn.execute(
                    "SELECT id, tier, timestamp, metrics_json FROM eval_metrics WHERE run_id = ? AND tier = ?",
                    (run_id, tier),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, tier, timestamp, metrics_json FROM eval_metrics WHERE run_id = ?",
                    (run_id,),
                ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get("metrics_json"):
                    d["metrics"] = json.loads(d["metrics_json"])
                    del d["metrics_json"]
                result.append(d)
            return result
