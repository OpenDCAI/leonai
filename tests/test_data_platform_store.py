from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from services.web.data_platform import store


def test_runs_and_events_roundtrip() -> None:
    with TemporaryDirectory() as td:
        db_path = Path(td) / "leon.db"
        store.ensure_tables(db_path)

        run_id = store.create_run(db_path=db_path, thread_id="t1", sandbox="local", input_message="hello")
        assert run_id

        ev1 = store.insert_event(db_path=db_path, run_id=run_id, thread_id="t1", event_type="run", payload={"x": 1})
        ev2 = store.insert_event(db_path=db_path, run_id=run_id, thread_id="t1", event_type="done", payload={"ok": True})
        assert ev2 > ev1

        run = store.get_run(db_path=db_path, run_id=run_id)
        assert run
        assert run.thread_id == "t1"
        assert run.status == "running"

        events = store.list_events(db_path=db_path, run_id=run_id, after_event_id=0, limit=10)
        assert [e.event_id for e in events] == [ev1, ev2]
        assert events[0].event_type == "run"
        assert events[1].event_type == "done"

        store.finalize_run(db_path=db_path, run_id=run_id, status="done")
        run2 = store.get_run(db_path=db_path, run_id=run_id)
        assert run2
        assert run2.status == "done"

