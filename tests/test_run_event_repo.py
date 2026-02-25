import sqlite3

from core.memory.run_event_repo import SQLiteRunEventRepo


def test_append_and_list_events_with_cursor(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        seq1 = repo.append_event("t-1", "r-1", "tool_call", {"name": "ls"}, "m-1")
        seq2 = repo.append_event("t-1", "r-1", "tool_result", {"ok": True}, "m-2")

        assert seq1 == 1
        assert seq2 == 2

        events = repo.list_events("t-1", "r-1", after=0)
        assert [event["event_type"] for event in events] == ["tool_call", "tool_result"]

        cursor_events = repo.list_events("t-1", "r-1", after=1)
        assert len(cursor_events) == 1
        assert cursor_events[0]["seq"] == 2
        assert cursor_events[0]["data"] == {"ok": True}
    finally:
        repo.close()


def test_latest_and_list_run_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        repo.append_event("t-2", "r-1", "status", {"s": 1})
        repo.append_event("t-2", "r-2", "status", {"s": 2})
        repo.append_event("t-2", "r-1", "status", {"s": 3})

        assert repo.latest_seq("t-2") == 3
        assert repo.latest_run_id("t-2") == "r-1"
        assert repo.list_run_ids("t-2") == ["r-1", "r-2"]
    finally:
        repo.close()


def test_delete_runs_and_thread_events(tmp_path):
    db_path = tmp_path / "leon.db"
    repo = SQLiteRunEventRepo(db_path)
    try:
        repo.append_event("t-3", "r-1", "status", {"v": 1})
        repo.append_event("t-3", "r-2", "status", {"v": 2})
        repo.append_event("t-3", "r-2", "status", {"v": 3})

        deleted = repo.delete_runs("t-3", ["r-2"])
        assert deleted == 2
        assert repo.list_run_ids("t-3") == ["r-1"]

        deleted_all = repo.delete_thread_events("t-3")
        assert deleted_all == 1
        assert repo.latest_seq("t-3") == 0

        with sqlite3.connect(str(db_path)) as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM run_events WHERE thread_id = ?", ("t-3",)).fetchone()[0]
            assert remaining == 0
    finally:
        repo.close()
