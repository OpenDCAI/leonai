"""Unit tests for RemoteSandbox._run_init_commands and RemoteSandbox.close()."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sandbox.base import RemoteSandbox
from sandbox.config import SandboxConfig
from sandbox.interfaces.executor import ExecuteResult
from sandbox.provider import ProviderCapability, SessionInfo


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


def _make_provider(on_init_exit_code: int = 0) -> MagicMock:
    provider = MagicMock()
    provider.name = "mock"
    provider.default_cwd = "/tmp"
    provider.get_capability.return_value = ProviderCapability(
        can_pause=True,
        can_resume=True,
        can_destroy=True,
        supports_webhook=False,
        supports_status_probe=False,
        eager_instance_binding=True,
        inspect_visible=True,
        runtime_kind="local",
    )
    provider.create_session.return_value = SessionInfo(
        session_id="inst-1",
        provider="mock",
        status="running",
    )
    provider.get_session_status.return_value = "running"
    provider.pause_session.return_value = True
    provider.resume_session.return_value = True
    provider.destroy_session.return_value = True

    # create_runtime returns a runtime whose execute() resolves to a result with the given exit code
    runtime = MagicMock()
    runtime.runtime_id = "runtime-test-000001"
    runtime.chat_session_id = None
    runtime.execute = AsyncMock(
        return_value=ExecuteResult(
            exit_code=on_init_exit_code,
            stdout="ok" if on_init_exit_code == 0 else "",
            stderr="" if on_init_exit_code == 0 else "fail",
        )
    )
    runtime.close = AsyncMock()
    provider.create_runtime.return_value = runtime
    return provider


def _make_sandbox(provider, db_path: Path, init_commands: list[str] | None = None, on_exit: str = "pause") -> RemoteSandbox:
    config = SandboxConfig(provider="mock", on_exit=on_exit, init_commands=init_commands or [])
    return RemoteSandbox(
        provider=provider,
        config=config,
        default_cwd="/tmp",
        db_path=db_path,
        name="mock",
        working_dir="/tmp",
        env_label="Mock",
    )


# ── _run_init_commands tests ────────────────────────────────────────────────


def test_run_init_commands_happy_path(temp_db):
    """Init commands that succeed are tracked per thread_id."""
    provider = _make_provider(on_init_exit_code=0)
    sandbox = _make_sandbox(provider, temp_db, init_commands=["echo hello"])

    from sandbox.thread_context import set_current_thread_id
    set_current_thread_id("thread-init-1")

    capability = sandbox._get_capability()
    assert capability is not None
    assert "thread-init-1" in sandbox._init_commands_run


def test_run_init_commands_failure_raises(temp_db):
    """Non-zero exit from init command raises RuntimeError with command+output in message."""
    provider = _make_provider(on_init_exit_code=1)
    sandbox = _make_sandbox(provider, temp_db, init_commands=["bad-cmd"])

    from sandbox.thread_context import set_current_thread_id
    set_current_thread_id("thread-init-fail")

    with pytest.raises(RuntimeError, match="Init command #1 failed"):
        sandbox._get_capability()


def test_run_init_commands_idempotent(temp_db):
    """Calling _get_capability() twice only runs init commands once per thread_id."""
    provider = _make_provider(on_init_exit_code=0)
    sandbox = _make_sandbox(provider, temp_db, init_commands=["echo once"])

    from sandbox.thread_context import set_current_thread_id
    set_current_thread_id("thread-init-2")

    sandbox._get_capability()
    sandbox._get_capability()  # second call — should not re-run init

    # execute was called once (for the single init command in the single init pass)
    runtime = provider.create_runtime.return_value
    assert runtime.execute.call_count == 1


# ── RemoteSandbox.close() tests ─────────────────────────────────────────────


def test_close_pause_calls_pause_all_sessions(temp_db):
    """on_exit=pause: pause_all_sessions() is called."""
    provider = _make_provider()
    sandbox = _make_sandbox(provider, temp_db, on_exit="pause")
    sandbox._manager.pause_all_sessions = MagicMock(return_value=2)

    sandbox.close()

    sandbox._manager.pause_all_sessions.assert_called_once()


def test_close_destroy_calls_destroy_for_each_session(temp_db):
    """on_exit=destroy: destroy_session() called for each session."""
    provider = _make_provider()
    sandbox = _make_sandbox(provider, temp_db, on_exit="destroy")

    fake_sessions = [{"thread_id": "t1"}, {"thread_id": "t2"}, {"thread_id": "t3"}]
    sandbox._manager.list_sessions = MagicMock(return_value=fake_sessions)
    sandbox._manager.destroy_session = MagicMock(return_value=True)

    sandbox.close()

    assert sandbox._manager.destroy_session.call_count == 3


def test_close_destroy_continues_after_one_failure(temp_db):
    """on_exit=destroy: a single destroy failure does not abort the remaining sessions."""
    provider = _make_provider()
    sandbox = _make_sandbox(provider, temp_db, on_exit="destroy")

    fake_sessions = [{"thread_id": "t1"}, {"thread_id": "t2"}, {"thread_id": "t3"}]
    sandbox._manager.list_sessions = MagicMock(return_value=fake_sessions)

    call_count = 0

    def side_effect(thread_id):
        nonlocal call_count
        call_count += 1
        if thread_id == "t2":
            raise RuntimeError("network error")
        return True

    sandbox._manager.destroy_session = MagicMock(side_effect=side_effect)

    sandbox.close()  # should not raise

    assert call_count == 3  # all 3 attempted despite t2 failure
