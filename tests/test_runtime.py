"""Unit tests for PhysicalTerminalRuntime."""

import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sandbox.lease import LeaseStore, SandboxInstance
from sandbox.provider import ProviderExecResult
from sandbox.runtime import (
    LocalPersistentShellRuntime,
    RemoteWrappedRuntime,
)
from sandbox.terminal import TerminalStore


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def terminal_store(temp_db):
    """Create TerminalStore with temp database."""
    return TerminalStore(db_path=temp_db)


@pytest.fixture
def lease_store(temp_db):
    """Create LeaseStore with temp database."""
    return LeaseStore(db_path=temp_db)


@pytest.fixture
def mock_provider():
    """Create mock SandboxProvider."""
    provider = MagicMock()
    provider.name = "test-provider"
    return provider


class TestLocalPersistentShellRuntime:
    """Test LocalPersistentShellRuntime."""

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, terminal_store, lease_store):
        """Test executing a simple command."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        result = await runtime.execute("echo 'hello world'")

        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert not result.timed_out

    @pytest.mark.asyncio
    async def test_execute_updates_cwd(self, terminal_store, lease_store):
        """Test that cwd is updated after command execution."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        # Execute cd command
        await runtime.execute("cd /")

        # Verify cwd updated
        state = runtime.get_terminal_state()
        assert state.cwd == "/"

    @pytest.mark.asyncio
    async def test_state_persists_across_commands(self, terminal_store, lease_store):
        """Test that state persists across multiple commands."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        # Change directory
        await runtime.execute("cd /")
        assert runtime.get_terminal_state().cwd == "/"

        # Execute another command - should still be in /
        result = await runtime.execute("pwd")
        assert "/" in result.stdout.strip()

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, terminal_store, lease_store):
        """Test command timeout."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        # Execute long-running command with short timeout
        result = await runtime.execute("sleep 10", timeout=0.1)

        assert result.timed_out
        assert result.exit_code == -1

    @pytest.mark.asyncio
    async def test_close_terminates_session(self, terminal_store, lease_store):
        """Test that close terminates the shell session."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        # Execute command to start session
        await runtime.execute("echo 'test'")
        assert runtime._session is not None

        # Close
        await runtime.close()

        # Session should be terminated
        assert runtime._session.returncode is not None

    @pytest.mark.asyncio
    async def test_state_version_increments(self, terminal_store, lease_store):
        """Test that state version increments after updates."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        assert runtime.get_terminal_state().state_version == 0

        # Execute command that changes cwd
        await runtime.execute("cd /")
        assert runtime.get_terminal_state().state_version == 1

        # Execute another command
        await runtime.execute("cd /tmp")
        assert runtime.get_terminal_state().state_version == 2


class TestRemoteWrappedRuntime:
    """Test RemoteWrappedRuntime."""

    @pytest.mark.asyncio
    async def test_execute_simple_command(self, terminal_store, lease_store, mock_provider):
        """Test executing a simple command via provider."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/root")
        lease = lease_store.create("lease-1", "test-provider")

        # Mock lease to return instance
        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="test-provider",
            status="running",
            created_at=None,
        )
        lease.ensure_active_instance = MagicMock(return_value=instance)

        # Mock provider execute
        mock_provider.execute.return_value = ProviderExecResult(
            exit_code=0,
            output="hello world",
            error=None,
        )

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)

        result = await runtime.execute("echo 'hello world'")

        assert result.exit_code == 0
        assert result.stdout == "hello world"
        mock_provider.execute.assert_called()

    @pytest.mark.asyncio
    async def test_hydrate_state_on_first_execution(self, terminal_store, lease_store, mock_provider):
        """Test that state is hydrated on first execution."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/home/user")
        lease = lease_store.create("lease-1", "test-provider")

        # Mock lease to return instance
        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="test-provider",
            status="running",
            created_at=None,
        )
        lease.ensure_active_instance = MagicMock(return_value=instance)

        # Mock provider execute
        mock_provider.execute.return_value = ProviderExecResult(
            exit_code=0,
            output="",
            error=None,
        )

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)

        await runtime.execute("echo 'test'")

        # Should have called cd to hydrate cwd
        calls = [str(call) for call in mock_provider.execute.call_args_list]
        assert any("cd /home/user" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_updates_cwd(self, terminal_store, lease_store, mock_provider):
        """Test that cwd is updated after command execution."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/root")
        lease = lease_store.create("lease-1", "test-provider")

        # Mock lease to return instance
        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="test-provider",
            status="running",
            created_at=None,
        )
        lease.ensure_active_instance = MagicMock(return_value=instance)

        # Mock provider execute
        def mock_execute(instance_id, command, **kwargs):
            start_match = re.search(r"__LEON_STATE_START_[a-f0-9]{8}__", command)
            end_match = re.search(r"__LEON_STATE_END_[a-f0-9]{8}__", command)
            if start_match and end_match:
                output = f"command output\n{start_match.group(0)}\n/home/user\nTEST_FLAG=1\n{end_match.group(0)}\n"
                return ProviderExecResult(exit_code=0, output=output, error=None)
            return ProviderExecResult(exit_code=0, output="", error=None)

        mock_provider.execute.side_effect = mock_execute

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)

        await runtime.execute("cd /home/user")

        # Verify cwd updated
        state = runtime.get_terminal_state()
        assert state.cwd == "/home/user"

    @pytest.mark.asyncio
    async def test_close_is_noop(self, terminal_store, lease_store, mock_provider):
        """Test that close is a no-op for remote runtime."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/root")
        lease = lease_store.create("lease-1", "test-provider")

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)

        # Close should not raise
        await runtime.close()

    @pytest.mark.asyncio
    async def test_infra_error_retries_once(self, terminal_store, lease_store, mock_provider):
        """Infra execution error should trigger one recovery retry."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/root")
        lease = lease_store.create("lease-1", "test-provider")

        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="test-provider",
            status="running",
            created_at=None,
        )
        lease.ensure_active_instance = MagicMock(return_value=instance)
        lease.refresh_instance_status = MagicMock(return_value="detached")

        mock_provider.execute.side_effect = [
            ProviderExecResult(exit_code=1, output="", error="session not found"),
            ProviderExecResult(exit_code=0, output="ok", error=None),
        ]

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)
        result = await runtime.execute("echo ok")

        assert result.exit_code == 0
        assert "ok" in result.stdout
        assert mock_provider.execute.call_count == 2
        assert lease.refresh_instance_status.call_count == 1

    @pytest.mark.asyncio
    async def test_non_infra_error_no_retry(self, terminal_store, lease_store, mock_provider):
        """Normal command failure should not trigger recovery retry."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/root")
        lease = lease_store.create("lease-1", "test-provider")

        instance = SandboxInstance(
            instance_id="inst-123",
            provider_name="test-provider",
            status="running",
            created_at=None,
        )
        lease.ensure_active_instance = MagicMock(return_value=instance)
        lease.refresh_instance_status = MagicMock(return_value="running")
        mock_provider.execute.return_value = ProviderExecResult(exit_code=2, output="grep: bad regex", error="")

        runtime = RemoteWrappedRuntime(terminal, lease, mock_provider)
        result = await runtime.execute("grep")

        assert result.exit_code == 2
        assert mock_provider.execute.call_count == 1
        assert lease.refresh_instance_status.call_count == 0


class TestRuntimeIntegration:
    """Integration tests for runtime lifecycle."""

    @pytest.mark.asyncio
    async def test_local_runtime_full_lifecycle(self, terminal_store, lease_store):
        """Test complete local runtime lifecycle."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        runtime = LocalPersistentShellRuntime(terminal, lease)

        # Execute multiple commands
        result1 = await runtime.execute("echo 'first'")
        assert "first" in result1.stdout

        result2 = await runtime.execute("cd /")
        assert result2.exit_code == 0

        result3 = await runtime.execute("pwd")
        assert "/" in result3.stdout

        # Verify state persisted
        state = runtime.get_terminal_state()
        assert state.cwd == "/"
        # State version increments: initial=0, after first execute=1, after cd=2, after pwd=3
        assert state.state_version >= 2

        # Close
        await runtime.close()

    @pytest.mark.asyncio
    async def test_state_persists_across_runtime_instances(self, terminal_store, lease_store):
        """Test that terminal state persists when runtime is recreated."""
        terminal = terminal_store.create("term-1", "thread-1", "lease-1", "/tmp")
        lease = lease_store.create("lease-1", "local")

        # First runtime
        runtime1 = LocalPersistentShellRuntime(terminal, lease)
        await runtime1.execute("cd /")
        await runtime1.close()

        # Retrieve terminal again
        terminal2 = terminal_store.get("thread-1")
        assert terminal2.get_state().cwd == "/"

        # Second runtime should start with persisted state
        runtime2 = LocalPersistentShellRuntime(terminal2, lease)
        result = await runtime2.execute("pwd")
        assert "/" in result.stdout

        await runtime2.close()
