import sqlite3
from pathlib import Path

import pytest

from core.storage.sqlite import SQLiteThreadMetadataRepo


def _create_thread_metadata_table(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE thread_metadata ("
            "thread_id TEXT PRIMARY KEY, "
            "sandbox_type TEXT NOT NULL, "
            "cwd TEXT, "
            "model TEXT)"
        )
        conn.commit()


def test_save_and_lookup_thread_metadata_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "leon.db"
    _create_thread_metadata_table(db_path)
    repo = SQLiteThreadMetadataRepo(db_path)

    repo.save_thread_metadata("t-1", "local", "/tmp/a")

    assert repo.lookup_thread_metadata("t-1") == ("local", "/tmp/a")
    assert repo.lookup_thread_model("t-1") is None


def test_save_thread_metadata_does_not_overwrite_existing_model(tmp_path: Path) -> None:
    db_path = tmp_path / "leon.db"
    _create_thread_metadata_table(db_path)
    repo = SQLiteThreadMetadataRepo(db_path)

    repo.save_thread_metadata("t-1", "local", "/tmp/a")
    repo.save_thread_model("t-1", "gpt-4.1")
    repo.save_thread_metadata("t-1", "remote", "/tmp/b")

    assert repo.lookup_thread_metadata("t-1") == ("remote", "/tmp/b")
    assert repo.lookup_thread_model("t-1") == "gpt-4.1"


def test_lookup_missing_row_returns_none(tmp_path: Path) -> None:
    db_path = tmp_path / "leon.db"
    _create_thread_metadata_table(db_path)
    repo = SQLiteThreadMetadataRepo(db_path)

    assert repo.lookup_thread_metadata("missing") is None
    assert repo.lookup_thread_model("missing") is None


def test_repo_fails_loudly_when_thread_metadata_table_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "leon.db"
    repo = SQLiteThreadMetadataRepo(db_path)

    with pytest.raises(sqlite3.OperationalError):
        repo.save_thread_metadata("t-1", "local", "/tmp/a")
