from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.web.data_platform.api import create_operator_router
from services.web.data_platform.store import create_run, ensure_tables


def test_operator_search_finds_runs() -> None:
    with TemporaryDirectory() as td:
        db_path = Path(td) / "dp.db"
        ensure_tables(db_path)

        run_id = create_run(db_path=db_path, thread_id="thread-xyz", sandbox="local", input_message="hello world")

        app = FastAPI()
        app.include_router(create_operator_router(dp_db_path=db_path))

        with TestClient(app) as client:
            resp = client.get("/api/operator/search", params={"q": run_id[:8], "limit": 50})
            assert resp.status_code == 200
            body = resp.json()
            assert body["count"] >= 1
            assert any(item["type"] == "run" and item["id"] == run_id for item in body["items"])

