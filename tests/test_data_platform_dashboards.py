from __future__ import annotations

import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.web.data_platform.api import create_operator_router
from services.web.data_platform.store import create_run, ensure_tables, finalize_run


def _set_started_at(db_path: Path, run_id: str, started_at: str) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE dp_runs SET started_at = ? WHERE run_id = ?", (started_at, run_id))
    conn.commit()
    conn.close()


def test_dashboards_overview_aggregates() -> None:
    with TemporaryDirectory() as td:
        dp_db_path = Path(td) / "dp.db"
        ensure_tables(dp_db_path)

        r_done = create_run(db_path=dp_db_path, thread_id="t1", sandbox="local", input_message="a")
        finalize_run(db_path=dp_db_path, run_id=r_done, status="done")

        r_err = create_run(db_path=dp_db_path, thread_id="t2", sandbox="local", input_message="b")
        finalize_run(db_path=dp_db_path, run_id=r_err, status="error", error="boom")

        r_stuck = create_run(db_path=dp_db_path, thread_id="t3", sandbox="local", input_message="c")
        _set_started_at(dp_db_path, r_stuck, "2020-01-01T00:00:00")

        app = FastAPI()
        app.include_router(create_operator_router(dp_db_path=dp_db_path))

        with TestClient(app) as client:
            resp = client.get("/api/operator/dashboards/overview", params={"window_hours": 24, "stuck_after_sec": 10})
            assert resp.status_code == 200
            body = resp.json()
            assert body["window_hours"] == 24
            assert body["runs_by_status"]["done"] == 1
            assert body["runs_by_status"]["error"] == 1
            assert body["stuck_runs"]["count"] == 1
            assert body["stuck_runs"]["items"][0]["run_id"] == r_stuck
            assert any(x["error"] == "boom" and x["count"] == 1 for x in body["top_errors"])

