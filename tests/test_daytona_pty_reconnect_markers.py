from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sandbox.runtime import DaytonaSessionRuntime, _RemoteRuntimeBase
from sandbox.interfaces.executor import ExecuteResult
from sandbox.terminal import TerminalState


@dataclass
class _DummyTerminal:
    terminal_id: str = "term-000000000000"

    def get_state(self) -> TerminalState:
        return TerminalState(cwd="/home/daytona", env_delta={}, state_version=0)

    def update_state(self, state: TerminalState) -> None:  # pragma: no cover
        pass


@dataclass
class _DummyLease:
    lease_id: str = "lease-000000000000"


@dataclass
class _DummyProvider:
    name: str = "daytona"


def test_infra_marker_matches_close_frame_error() -> None:
    msg = "Error: Failed to send input to PTY: no close frame received or sent"
    assert _RemoteRuntimeBase._looks_like_infra_error(msg) is True


def test_daytona_runtime_retries_on_close_frame_error() -> None:
    terminal = _DummyTerminal()
    lease = _DummyLease()
    provider = _DummyProvider()
    rt = DaytonaSessionRuntime(terminal=terminal, lease=lease, provider=provider)  # type: ignore[arg-type]

    calls = {"count": 0, "recover": 0, "close": 0}

    def _fake_execute_once_sync(command: str, timeout=None, on_stdout_chunk=None):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Failed to send input to PTY: no close frame received or sent")
        return ExecuteResult(exit_code=0, stdout="ok\n", stderr="")

    rt._execute_once_sync = _fake_execute_once_sync  # type: ignore[method-assign]
    rt._recover_infra = lambda: calls.__setitem__("recover", calls["recover"] + 1)  # type: ignore[method-assign]
    rt._close_shell_sync = lambda: calls.__setitem__("close", calls["close"] + 1)  # type: ignore[method-assign]

    result = asyncio.run(rt.execute("echo hi", timeout=5))
    assert result.exit_code == 0
    assert result.stdout == "ok\n"
    assert calls["count"] == 2
    assert calls["recover"] == 1
    assert calls["close"] == 1

