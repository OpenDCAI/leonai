"""StorageContainer — phase-3 composition root for hunter worktree.

# @@@phase3-container - wires all 6 phase-2 repos; call sites unchanged.
"""

from __future__ import annotations

from pathlib import Path


class StorageContainer:
    """Composition root: instantiates phase-2 repos from DB paths."""

    def __init__(
        self,
        main_db_path: str | Path | None = None,
        eval_db_path: str | Path | None = None,
    ) -> None:
        root = Path.home() / ".leon"
        self._main_db = Path(main_db_path) if main_db_path else root / "leon.db"
        self._eval_db = Path(eval_db_path) if eval_db_path else root / "eval.db"

    def checkpoint_repo(self):
        from core.memory.checkpoint_repo import SQLiteCheckpointRepo
        return SQLiteCheckpointRepo(db_path=self._main_db)

    def thread_config_repo(self):
        from core.memory.thread_config_repo import SQLiteThreadConfigRepo
        return SQLiteThreadConfigRepo(db_path=self._main_db)

    def run_event_repo(self):
        from core.memory.run_event_repo import SQLiteRunEventRepo
        return SQLiteRunEventRepo(db_path=self._main_db)

    def file_operation_repo(self):
        from core.memory.file_operation_repo import SQLiteFileOperationRepo
        return SQLiteFileOperationRepo(db_path=self._main_db)

    def summary_repo(self):
        import sqlite3
        from core.memory.summary_repo import SQLiteSummaryRepo
        return SQLiteSummaryRepo(
            db_path=self._main_db,
            connect_fn=lambda p: sqlite3.connect(str(p)),
        )

    def eval_repo(self):
        from eval.repo import SQLiteEvalRepo
        return SQLiteEvalRepo(db_path=self._eval_db)
