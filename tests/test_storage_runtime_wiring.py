"""Runtime storage wiring tests for backend agent creation path."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from backend.web.services import agent_pool
from backend.web.services.event_buffer import RunEventBuffer
from backend.web.services.streaming_service import _run_agent_to_buffer
from core.storage.providers.sqlite.checkpoint_repo import SQLiteCheckpointRepo
from core.storage.providers.sqlite.eval_repo import SQLiteEvalRepo
from core.storage.providers.supabase.checkpoint_repo import SupabaseCheckpointRepo


class _FakeSupabaseClient:
    def table(self, table_name: str):
        raise AssertionError(f"table() should not be called in this wiring test: {table_name}")


def _build_fake_supabase_client() -> _FakeSupabaseClient:
    return _FakeSupabaseClient()


def _build_invalid_supabase_client() -> object:
    return object()


def _capture_create_leon_agent(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def _fake_create_leon_agent(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(agent_pool, "create_leon_agent", _fake_create_leon_agent)
    return captured


def test_create_agent_sync_wires_supabase_storage_container(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "supabase")
    monkeypatch.setenv(
        "LEON_SUPABASE_CLIENT_FACTORY",
        "tests.test_storage_runtime_wiring:_build_fake_supabase_client",
    )
    monkeypatch.setenv("LEON_DB_PATH", str(tmp_path / "leon.db"))
    monkeypatch.setenv("LEON_EVAL_DB_PATH", str(tmp_path / "eval.db"))

    captured = _capture_create_leon_agent(monkeypatch)
    agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")

    container = captured["storage_container"]
    assert isinstance(container.checkpoint_repo(), SupabaseCheckpointRepo)


def test_create_agent_sync_supabase_missing_runtime_config_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "supabase")
    monkeypatch.delenv("LEON_SUPABASE_CLIENT_FACTORY", raising=False)

    with pytest.raises(
        RuntimeError,
        match="LEON_SUPABASE_CLIENT_FACTORY",
    ):
        agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")


def test_create_agent_sync_supabase_invalid_runtime_config_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "supabase")
    monkeypatch.setenv(
        "LEON_SUPABASE_CLIENT_FACTORY",
        "tests.test_storage_runtime_wiring:_build_invalid_supabase_client",
    )

    with pytest.raises(RuntimeError, match="callable table\\(name\\) API"):
        agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")


def test_create_agent_sync_defaults_to_sqlite_storage_container(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LEON_STORAGE_STRATEGY", raising=False)
    monkeypatch.delenv("LEON_SUPABASE_CLIENT_FACTORY", raising=False)
    monkeypatch.setenv("LEON_DB_PATH", str(tmp_path / "leon.db"))

    captured = _capture_create_leon_agent(monkeypatch)
    agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")

    container = captured["storage_container"]
    assert isinstance(container.checkpoint_repo(), SQLiteCheckpointRepo)


def test_create_agent_sync_repo_override_supabase_with_sqlite_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "sqlite")
    monkeypatch.setenv("LEON_STORAGE_REPO_PROVIDERS", '{"checkpoint_repo":"supabase"}')
    monkeypatch.setenv(
        "LEON_SUPABASE_CLIENT_FACTORY",
        "tests.test_storage_runtime_wiring:_build_fake_supabase_client",
    )
    monkeypatch.setenv("LEON_DB_PATH", str(tmp_path / "leon.db"))

    captured = _capture_create_leon_agent(monkeypatch)
    agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")
    container = captured["storage_container"]
    assert isinstance(container.checkpoint_repo(), SupabaseCheckpointRepo)


def test_create_agent_sync_repo_override_sqlite_with_supabase_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "supabase")
    monkeypatch.setenv("LEON_STORAGE_REPO_PROVIDERS", '{"eval_repo":"sqlite"}')
    monkeypatch.setenv(
        "LEON_SUPABASE_CLIENT_FACTORY",
        "tests.test_storage_runtime_wiring:_build_fake_supabase_client",
    )
    monkeypatch.setenv("LEON_DB_PATH", str(tmp_path / "leon.db"))
    monkeypatch.setenv("LEON_EVAL_DB_PATH", str(tmp_path / "eval.db"))

    captured = _capture_create_leon_agent(monkeypatch)
    agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")
    container = captured["storage_container"]
    assert isinstance(container.eval_repo(), SQLiteEvalRepo)


def test_create_agent_sync_all_sqlite_override_with_supabase_default_does_not_require_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "supabase")
    monkeypatch.setenv(
        "LEON_STORAGE_REPO_PROVIDERS",
        (
            '{"checkpoint_repo":"sqlite","thread_config_repo":"sqlite","run_event_repo":"sqlite",'
            '"file_operation_repo":"sqlite","summary_repo":"sqlite","eval_repo":"sqlite"}'
        ),
    )
    monkeypatch.delenv("LEON_SUPABASE_CLIENT_FACTORY", raising=False)
    monkeypatch.setenv("LEON_DB_PATH", str(tmp_path / "leon.db"))
    monkeypatch.setenv("LEON_EVAL_DB_PATH", str(tmp_path / "eval.db"))

    captured = _capture_create_leon_agent(monkeypatch)
    agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")
    container = captured["storage_container"]
    assert isinstance(container.checkpoint_repo(), SQLiteCheckpointRepo)


def test_create_agent_sync_repo_override_supabase_without_runtime_config_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_STRATEGY", "sqlite")
    monkeypatch.setenv("LEON_STORAGE_REPO_PROVIDERS", '{"checkpoint_repo":"supabase"}')
    monkeypatch.delenv("LEON_SUPABASE_CLIENT_FACTORY", raising=False)

    with pytest.raises(RuntimeError, match="LEON_SUPABASE_CLIENT_FACTORY"):
        agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")


def test_create_agent_sync_invalid_repo_override_json_fails_loud(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("LEON_STORAGE_REPO_PROVIDERS", "not-json")

    with pytest.raises(RuntimeError, match="Invalid LEON_STORAGE_REPO_PROVIDERS"):
        agent_pool.create_agent_sync("local", workspace_root=tmp_path, model_name="leon:test")


class _FakeRunEventRepo:
    def __init__(self) -> None:
        self.append_calls: list[dict[str, Any]] = []
        self.closed = False

    def append_event(
        self,
        thread_id: str,
        run_id: str,
        event_type: str,
        data: dict[str, Any],
        message_id: str | None = None,
    ) -> int:
        self.append_calls.append(
            {
                "thread_id": thread_id,
                "run_id": run_id,
                "event_type": event_type,
                "data": data,
                "message_id": message_id,
            }
        )
        return len(self.append_calls)

    def list_run_ids(self, thread_id: str) -> list[str]:
        return []

    def delete_runs(self, thread_id: str, run_ids: list[str]) -> int:
        return 0

    def close(self) -> None:
        self.closed = True


class _FakeStorageContainer:
    def __init__(self, repo: _FakeRunEventRepo) -> None:
        self._repo = repo

    def run_event_repo(self) -> _FakeRunEventRepo:
        return self._repo


class _FakeGraphAgent:
    checkpointer = None

    async def astream(self, *_args: Any, **_kwargs: Any):
        if False:  # pragma: no cover
            yield None


class _FakeRuntime:
    current_state = "IDLE"

    def get_pending_subagent_events(self) -> list[tuple[str, list[dict[str, Any]]]]:
        return []

    def get_status_dict(self) -> dict[str, Any]:
        return {}


class _FakeRuntimeAgent:
    def __init__(self, storage_container: Any = None) -> None:
        self.agent = _FakeGraphAgent()
        self.storage_container = storage_container
        self.runtime = _FakeRuntime()


def test_run_runtime_consumes_storage_container_run_event_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        import backend.web.services.event_store as event_store

        async def _raise_if_sqlite_conn_used() -> Any:
            raise AssertionError("sqlite connection path should not be used when storage container repo is present")

        monkeypatch.setattr(event_store, "_get_conn", _raise_if_sqlite_conn_used)

        repo = _FakeRunEventRepo()
        agent = _FakeRuntimeAgent(storage_container=_FakeStorageContainer(repo))
        app = SimpleNamespace(state=SimpleNamespace(thread_tasks={}, thread_event_buffers={}))
        buf = RunEventBuffer()
        buf.run_id = "run-1"

        await _run_agent_to_buffer(agent, "thread-1", "hello", app, False, buf)

        assert repo.append_calls, "run path should persist events through storage_container.run_event_repo()"
        assert any(c["event_type"] == "done" for c in repo.append_calls)
        assert repo.closed is True

    asyncio.run(_run())


def test_run_runtime_without_storage_container_keeps_sqlite_event_store_path(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        import backend.web.services.event_store as event_store

        calls: list[dict[str, Any]] = []

        async def _fake_append_event(
            thread_id: str,
            run_id: str,
            event: dict[str, Any],
            message_id: str | None = None,
            run_event_repo: Any | None = None,
        ) -> int:
            calls.append(
                {
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "event": event,
                    "message_id": message_id,
                    "run_event_repo": run_event_repo,
                }
            )
            return len(calls)

        async def _fake_cleanup_old_runs(
            thread_id: str,
            keep_latest: int = 1,
            run_event_repo: Any | None = None,
        ) -> int:
            return 0

        monkeypatch.setattr(event_store, "append_event", _fake_append_event)
        monkeypatch.setattr(event_store, "cleanup_old_runs", _fake_cleanup_old_runs)

        agent = _FakeRuntimeAgent(storage_container=None)
        app = SimpleNamespace(state=SimpleNamespace(thread_tasks={}, thread_event_buffers={}))
        buf = RunEventBuffer()
        buf.run_id = "run-1"

        await _run_agent_to_buffer(agent, "thread-1", "hello", app, False, buf)

        assert calls, "sqlite event store path should still be used when no storage container is injected"
        assert all(call["run_event_repo"] is None for call in calls)

    asyncio.run(_run())
