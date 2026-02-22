import inspect
import sqlite3
from pathlib import Path

import pytest

from backend.web.utils import helpers
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


def test_metadata_helper_signatures_remain_stable() -> None:
    assert tuple(inspect.signature(helpers.save_thread_metadata).parameters) == ("thread_id", "sandbox_type", "cwd")
    assert tuple(inspect.signature(helpers.save_thread_model).parameters) == ("thread_id", "model")
    assert tuple(inspect.signature(helpers.lookup_thread_model).parameters) == ("thread_id",)
    assert tuple(inspect.signature(helpers.lookup_thread_metadata).parameters) == ("thread_id",)


def test_metadata_helpers_match_repo_behavior(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "leon.db"
    _create_thread_metadata_table(db_path)
    repo = SQLiteThreadMetadataRepo(db_path)
    monkeypatch.setattr(helpers, "_thread_metadata_repo", repo)

    helpers.save_thread_metadata("t-1", "local", "/tmp/a")
    helpers.save_thread_model("t-1", "gpt-4.1")

    assert helpers.lookup_thread_metadata("t-1") == repo.lookup_thread_metadata("t-1")
    assert helpers.lookup_thread_model("t-1") == repo.lookup_thread_model("t-1")


def test_metadata_helpers_fail_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "leon.db"
    repo = SQLiteThreadMetadataRepo(db_path)
    monkeypatch.setattr(helpers, "_thread_metadata_repo", repo)

    with pytest.raises(sqlite3.OperationalError):
        helpers.lookup_thread_metadata("t-1")
