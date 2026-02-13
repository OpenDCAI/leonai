import tempfile
from pathlib import Path

import pytest

from sandbox.runtime import DaytonaSessionRuntime, ExecuteResult
from sandbox.terminal import TerminalState


class _DummyTerminal:
    def __init__(self, db_path: Path):
        self.terminal_id = "term-1"
        self.thread_id = "thread-1"
        self.lease_id = "lease-1"
        self.db_path = db_path
        self._state = TerminalState(cwd="/home/daytona", env_delta={})

    def get_state(self) -> TerminalState:
        return self._state

    def update_state(self, state: TerminalState) -> None:
        self._state = state


@pytest.mark.asyncio
async def test_snapshot_error_infra_does_not_wedge_runtime():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    try:
        terminal = _DummyTerminal(db_path)
        lease = object()
        provider = object()
        runtime = DaytonaSessionRuntime(terminal, lease, provider)

        # Simulate a prior async snapshot failure (seen in production threads).
        runtime._snapshot_error = "Command timed out after 3.0s"

        calls: list[str] = []
        runtime._recover_infra = lambda: calls.append("recover")  # type: ignore[method-assign]
        runtime._close_shell_sync = lambda: calls.append("close")  # type: ignore[method-assign]

        def _execute_once_sync(_cmd: str, _timeout: float | None, _on=None) -> ExecuteResult:
            return ExecuteResult(exit_code=0, stdout="ok", stderr="")

        runtime._execute_once_sync = _execute_once_sync  # type: ignore[method-assign]

        snapshot_timeouts: list[float | None] = []
        runtime._schedule_snapshot = lambda _gen, t: snapshot_timeouts.append(t)  # type: ignore[method-assign]

        result = await runtime.execute("echo hi", timeout=1.0)

        assert result.exit_code == 0
        assert runtime._snapshot_error is None
        assert calls == ["recover", "close"]
        assert snapshot_timeouts, "should schedule a fresh snapshot after command"
        assert snapshot_timeouts[-1] is not None and snapshot_timeouts[-1] >= 10.0
    finally:
        db_path.unlink(missing_ok=True)
