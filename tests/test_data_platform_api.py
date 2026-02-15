from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.web.data_platform.api import create_router
from services.web.data_platform.store import ensure_tables, insert_event, create_run


def test_api_run_and_events_cursor() -> None:
    with TemporaryDirectory() as td:
        db_path = Path(td) / "leon.db"
        ensure_tables(db_path)

        run_id = create_run(db_path=db_path, thread_id="t1", sandbox="local", input_message="hi")
        insert_event(db_path=db_path, run_id=run_id, thread_id="t1", event_type="run", payload={"run_id": run_id})
        insert_event(db_path=db_path, run_id=run_id, thread_id="t1", event_type="done", payload={"ok": True})

        app = FastAPI()
        app.include_router(create_router(db_path=db_path))

        with TestClient(app) as client:
            r1 = client.get(f"/api/runs/{run_id}")
            assert r1.status_code == 200
            assert r1.json()["run_id"] == run_id

            r2 = client.get(f"/api/runs/{run_id}/events?after_event_id=0&limit=10")
            assert r2.status_code == 200
            body = r2.json()
            assert body["run_id"] == run_id
            assert len(body["items"]) == 2
            assert body["items"][0]["event_type"] == "run"
            assert body["items"][1]["event_type"] == "done"

