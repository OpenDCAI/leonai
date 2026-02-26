import sqlite3
from pathlib import Path

import backend.web.utils.helpers as helpers


def _seed_thread_table(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE thread_events (thread_id TEXT, payload TEXT)")
        conn.execute("INSERT INTO thread_events (thread_id, payload) VALUES (?, ?)", ("target-thread", "drop-me"))
        conn.execute("INSERT INTO thread_events (thread_id, payload) VALUES (?, ?)", ("keep-thread", "keep-me"))
        conn.execute("CREATE TABLE misc_data (value TEXT)")
        conn.execute("INSERT INTO misc_data (value) VALUES (?)", ("untouched",))
        conn.commit()


def _read_thread_events(db_path: Path) -> list[tuple[str, str]]:
    with sqlite3.connect(str(db_path)) as conn:
        return conn.execute(
            "SELECT thread_id, payload FROM thread_events ORDER BY thread_id"
        ).fetchall()


def test_delete_thread_in_db_deletes_target_thread_from_both_databases(tmp_path, monkeypatch):
    app_db = tmp_path / "app.db"
    sandbox_db = tmp_path / "sandbox.db"
    _seed_thread_table(app_db)
    _seed_thread_table(sandbox_db)

    monkeypatch.setattr(helpers, "DB_PATH", app_db)
    monkeypatch.setattr(helpers, "SANDBOX_DB_PATH", sandbox_db)

    helpers.delete_thread_in_db("target-thread")

    assert _read_thread_events(app_db) == [("keep-thread", "keep-me")]
    assert _read_thread_events(sandbox_db) == [("keep-thread", "keep-me")]

    with sqlite3.connect(str(app_db)) as conn:
        assert conn.execute("SELECT value FROM misc_data").fetchall() == [("untouched",)]


def test_delete_thread_in_db_skips_invalid_sqlite_identifier_tables(tmp_path, monkeypatch):
    app_db = tmp_path / "app.db"
    missing_sandbox_db = tmp_path / "missing-sandbox.db"

    with sqlite3.connect(str(app_db)) as conn:
        conn.execute("CREATE TABLE thread_events (thread_id TEXT, payload TEXT)")
        conn.execute("INSERT INTO thread_events (thread_id, payload) VALUES (?, ?)", ("target-thread", "drop-me"))
        # @@@invalid-sqlite-ident - Quoted table names can contain '-' but helper intentionally skips them.
        conn.execute('CREATE TABLE "bad-table" (thread_id TEXT, payload TEXT)')
        conn.execute('INSERT INTO "bad-table" (thread_id, payload) VALUES (?, ?)', ("target-thread", "blocked"))
        conn.commit()

    monkeypatch.setattr(helpers, "DB_PATH", app_db)
    monkeypatch.setattr(helpers, "SANDBOX_DB_PATH", missing_sandbox_db)

    helpers.delete_thread_in_db("target-thread")

    with sqlite3.connect(str(app_db)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM thread_events").fetchone() == (0,)
        assert conn.execute('SELECT thread_id, payload FROM "bad-table"').fetchall() == [
            ("target-thread", "blocked")
        ]
