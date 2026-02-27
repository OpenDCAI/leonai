"""Storage container with repo-level provider selection."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal
import sqlite3

StorageStrategy = Literal["sqlite", "supabase"]
RepoProviderMap = Mapping[str, str]


class StorageContainer:
    """Composition root for storage repos."""

    _SUPPORTED_STRATEGIES = {"sqlite", "supabase"}
    _REPO_NAMES = (
        "checkpoint_repo",
        "thread_config_repo",
        "run_event_repo",
        "file_operation_repo",
        "summary_repo",
        "eval_repo",
    )

    def __init__(
        self,
        main_db_path: str | Path | None = None,
        eval_db_path: str | Path | None = None,
        strategy: StorageStrategy = "sqlite",
        repo_providers: RepoProviderMap | None = None,
        supabase_bindings: Mapping[str, Any] | None = None,
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
        self._repo_providers = self._resolve_repo_providers(
            default_strategy=strategy,
            repo_providers=repo_providers,
            legacy_supabase_bindings=supabase_bindings,
        )

    def checkpoint_repo(self):
        if self._provider_for("checkpoint_repo") == "supabase":
            return self._build_supabase_checkpoint_repo()
        from core.storage.providers.sqlite.checkpoint_repo import SQLiteCheckpointRepo
        return SQLiteCheckpointRepo(db_path=self._main_db)

    def thread_config_repo(self):
        if self._provider_for("thread_config_repo") == "supabase":
            return self._build_supabase_thread_config_repo()
        from core.storage.providers.sqlite.thread_config_repo import SQLiteThreadConfigRepo
        return SQLiteThreadConfigRepo(db_path=self._main_db)

    def run_event_repo(self):
        if self._provider_for("run_event_repo") == "supabase":
            return self._build_supabase_run_event_repo()
        from core.storage.providers.sqlite.run_event_repo import SQLiteRunEventRepo
        return SQLiteRunEventRepo(db_path=self._main_db)

    def file_operation_repo(self):
        if self._provider_for("file_operation_repo") == "supabase":
            return self._build_supabase_file_operation_repo()
        from core.storage.providers.sqlite.file_operation_repo import SQLiteFileOperationRepo
        return SQLiteFileOperationRepo(db_path=self._main_db)

    def summary_repo(self):
        if self._provider_for("summary_repo") == "supabase":
            return self._build_supabase_summary_repo()
        from core.storage.providers.sqlite.summary_repo import SQLiteSummaryRepo
        return SQLiteSummaryRepo(
            db_path=self._main_db,
            connect_fn=lambda p: sqlite3.connect(str(p)),
        )

    def eval_repo(self):
        if self._provider_for("eval_repo") == "supabase":
            return self._build_supabase_eval_repo()
        from core.storage.providers.sqlite.eval_repo import SQLiteEvalRepo
        return SQLiteEvalRepo(db_path=self._eval_db)

    def provider_for(self, repo_name: str) -> StorageStrategy:
        return self._provider_for(repo_name)

    def _provider_for(self, repo_name: str) -> StorageStrategy:
        if repo_name not in self._REPO_NAMES:
            supported = ", ".join(self._REPO_NAMES)
            raise ValueError(f"Unknown repo name: {repo_name}. Supported repo names: {supported}")
        return self._repo_providers[repo_name]

    @classmethod
    def _resolve_repo_providers(
        cls,
        *,
        default_strategy: StorageStrategy,
        repo_providers: RepoProviderMap | None,
        legacy_supabase_bindings: Mapping[str, Any] | None,
    ) -> dict[str, StorageStrategy]:
        if repo_providers is not None and legacy_supabase_bindings is not None:
            raise ValueError("Use either repo_providers or supabase_bindings, not both.")

        overrides: Mapping[str, Any] = repo_providers or legacy_supabase_bindings or {}
        unknown_repos = sorted(set(overrides.keys()) - set(cls._REPO_NAMES))
        if unknown_repos:
            supported = ", ".join(cls._REPO_NAMES)
            unknown = ", ".join(unknown_repos)
            raise ValueError(f"Unknown repo provider bindings: {unknown}. Supported repo names: {supported}")

        resolved: dict[str, StorageStrategy] = {name: default_strategy for name in cls._REPO_NAMES}
        # @@@repo-provider-override - default strategy keeps current behavior; only explicitly listed repos diverge.
        for repo_name, provider in overrides.items():
            if not isinstance(provider, str):
                raise ValueError(
                    f"Invalid provider value for {repo_name}: {provider!r}. Expected 'sqlite' or 'supabase'."
                )
            normalized = provider.strip().lower()
            if normalized not in cls._SUPPORTED_STRATEGIES:
                supported = ", ".join(sorted(cls._SUPPORTED_STRATEGIES))
                raise ValueError(
                    f"Unsupported provider for {repo_name}: {provider!r}. Supported providers: {supported}"
                )
            resolved[repo_name] = normalized
        return resolved

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
