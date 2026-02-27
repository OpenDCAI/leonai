"""StorageContainer — phase-3 composition root for hunter worktree.

# @@@phase3-container - wires all 6 phase-2 repos; call sites unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

StorageStrategy = Literal["sqlite", "supabase"]
RepoBindingMap = Mapping[str, Any]


class StorageContainer:
    """Composition root: instantiates phase-2 repos from DB paths."""

    _SUPPORTED_STRATEGIES = {"sqlite", "supabase"}

    def __init__(
        self,
        main_db_path: str | Path | None = None,
        eval_db_path: str | Path | None = None,
        strategy: StorageStrategy = "sqlite",
        supabase_bindings: RepoBindingMap | None = None,
        supabase_client: Any | None = None,
    ) -> None:
        if strategy not in self._SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Unsupported storage strategy: {strategy}. "
                f"Supported strategies: {', '.join(sorted(self._SUPPORTED_STRATEGIES))}"
            )
        root = Path.home() / ".leon"
        self._main_db = Path(main_db_path) if main_db_path else root / "leon.db"
        self._eval_db = Path(eval_db_path) if eval_db_path else root / "eval.db"
        self._strategy: StorageStrategy = strategy
        self._supabase_client = supabase_client

    def checkpoint_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_checkpoint_repo()
        from core.storage.providers.sqlite.checkpoint_repo import SQLiteCheckpointRepo
        return SQLiteCheckpointRepo(db_path=self._main_db)

    def thread_config_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_thread_config_repo()
        from core.storage.providers.sqlite.thread_config_repo import SQLiteThreadConfigRepo
        return SQLiteThreadConfigRepo(db_path=self._main_db)

    def run_event_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_run_event_repo()
        from core.storage.providers.sqlite.run_event_repo import SQLiteRunEventRepo
        return SQLiteRunEventRepo(db_path=self._main_db)

    def file_operation_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_file_operation_repo()
        from core.storage.providers.sqlite.file_operation_repo import SQLiteFileOperationRepo
        return SQLiteFileOperationRepo(db_path=self._main_db)

    def summary_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_summary_repo()
        import sqlite3
        from core.storage.providers.sqlite.summary_repo import SQLiteSummaryRepo
        return SQLiteSummaryRepo(
            db_path=self._main_db,
            connect_fn=lambda p: sqlite3.connect(str(p)),
        )

    def eval_repo(self):
        if self._strategy == "supabase":
            return self._build_supabase_eval_repo()
        from core.storage.providers.sqlite.eval_repo import SQLiteEvalRepo
        return SQLiteEvalRepo(db_path=self._eval_db)

    def _build_supabase_checkpoint_repo(self):
        from core.storage.providers.supabase.checkpoint_repo import SupabaseCheckpointRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy checkpoint_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseCheckpointRepo(client=self._supabase_client)

    def _build_supabase_thread_config_repo(self):
        from core.storage.providers.supabase.thread_config_repo import SupabaseThreadConfigRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy thread_config_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseThreadConfigRepo(client=self._supabase_client)

    def _build_supabase_run_event_repo(self):
        from core.storage.providers.supabase.run_event_repo import SupabaseRunEventRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy run_event_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseRunEventRepo(client=self._supabase_client)

    def _build_supabase_file_operation_repo(self):
        from core.storage.providers.supabase.file_operation_repo import SupabaseFileOperationRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy file_operation_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseFileOperationRepo(client=self._supabase_client)

    def _build_supabase_summary_repo(self):
        from core.storage.providers.supabase.summary_repo import SupabaseSummaryRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy summary_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseSummaryRepo(client=self._supabase_client)

    def _build_supabase_eval_repo(self):
        from core.storage.providers.supabase.eval_repo import SupabaseEvalRepo

        if self._supabase_client is None:
            raise RuntimeError(
                "Supabase strategy eval_repo requires supabase_client. "
                "Pass supabase_client=... into StorageContainer."
            )
        return SupabaseEvalRepo(client=self._supabase_client)
