import sqlite3
from pathlib import Path

from core.memory.checkpoint_repo import SQLiteCheckpointRepo


def _setup_tables(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE checkpoints (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE writes (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE checkpoint_writes (thread_id TEXT, checkpoint_id TEXT)")
        conn.execute("CREATE TABLE checkpoint_blobs (thread_id TEXT, checkpoint_id TEXT)")
        conn.commit()


def test_list_thread_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-2", "c1"))
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-1", "c2"))
        conn.execute("INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)", ("t-1", "c3"))
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        assert repo.list_thread_ids() == ["t-1", "t-2"]
    finally:
        repo.close()


def test_delete_checkpoints_by_ids(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_blobs (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c2"), ("t-1", "c3"), ("t-2", "c2")],
        )
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        repo.delete_checkpoints_by_ids("t-1", ["c2", "c3"])
    finally:
        repo.close()

    with sqlite3.connect(str(db_path)) as conn:
        left_checkpoints = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoints ORDER BY thread_id, checkpoint_id"
        ).fetchall()
        left_writes = conn.execute("SELECT thread_id, checkpoint_id FROM writes ORDER BY thread_id, checkpoint_id").fetchall()
        left_cp_writes = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoint_writes ORDER BY thread_id, checkpoint_id"
        ).fetchall()
        left_cp_blobs = conn.execute(
            "SELECT thread_id, checkpoint_id FROM checkpoint_blobs ORDER BY thread_id, checkpoint_id"
        ).fetchall()

    assert left_checkpoints == [("t-1", "c1"), ("t-2", "c2")]
    assert left_writes == [("t-2", "c2")]
    assert left_cp_writes == [("t-2", "c2")]
    assert left_cp_blobs == [("t-2", "c2")]


def test_delete_thread_data(tmp_path):
    db_path = tmp_path / "leon.db"
    _setup_tables(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executemany(
            "INSERT INTO checkpoints (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_writes (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.executemany(
            "INSERT INTO checkpoint_blobs (thread_id, checkpoint_id) VALUES (?, ?)",
            [("t-1", "c1"), ("t-2", "c2")],
        )
        conn.commit()

    repo = SQLiteCheckpointRepo(db_path=db_path)
    try:
        repo.delete_thread_data("t-1")
    finally:
        repo.close()

    with sqlite3.connect(str(db_path)) as conn:
        left_checkpoints = conn.execute("SELECT thread_id FROM checkpoints ORDER BY thread_id").fetchall()
        left_writes = conn.execute("SELECT thread_id FROM writes ORDER BY thread_id").fetchall()
        left_cp_writes = conn.execute("SELECT thread_id FROM checkpoint_writes ORDER BY thread_id").fetchall()
        left_cp_blobs = conn.execute("SELECT thread_id FROM checkpoint_blobs ORDER BY thread_id").fetchall()

    assert left_checkpoints == [("t-2",)]
    assert left_writes == [("t-2",)]
    assert left_cp_writes == [("t-2",)]
    assert left_cp_blobs == [("t-2",)]
