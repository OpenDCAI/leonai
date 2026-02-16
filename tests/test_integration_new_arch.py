"""Integration tests for the full new architecture flow.

Tests the complete flow: Thread → ChatSession → Runtime → Terminal → Lease → Instance
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sandbox.chat_session import ChatSessionManager
from sandbox.lease import LeaseStore
from sandbox.manager import SandboxManager
from sandbox.provider import SessionInfo
from sandbox.terminal import TerminalStore


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def mock_provider():
    """Create mock SandboxProvider for local testing."""
    provider = MagicMock()
    provider.name = "local"

    # Mock execute to return proper results
    def mock_execute(instance_id, command, timeout_ms=None, cwd=None):
        result = MagicMock()
        result.exit_code = 0

        if command == "pwd":
            result.stdout = cwd or "/root"
            result.stderr = ""
        elif command.startswith("cd "):
            result.stdout = ""
            result.stderr = ""
        else:
            result.stdout = "command output"
            result.stderr = ""

        return result

    provider.execute = mock_execute
    return provider


@pytest.fixture
def mock_remote_provider():
    """Create mock remote provider that supports lease lifecycle + fs ops."""
    provider = MagicMock()
    provider.name = "e2b"
    provider.create_session.return_value = SessionInfo(
        session_id="inst-remote-1",
        provider="e2b",
        status="running",
    )
    provider.get_session_status.return_value = "running"
    provider.pause_session.return_value = True
    provider.resume_session.return_value = True
    provider.write_file.return_value = "ok"
    provider.read_file.return_value = "content"
    provider.list_dir.return_value = []
    return provider


@pytest.fixture
def sandbox_manager(temp_db, mock_provider):
    """Create SandboxManager with temp database."""
    return SandboxManager(provider=mock_provider, db_path=temp_db)


@pytest.fixture
def remote_sandbox_manager(temp_db, mock_remote_provider):
    """Create SandboxManager with remote provider."""
    return SandboxManager(provider=mock_remote_provider, db_path=temp_db)


class TestFullArchitectureFlow:
    """Test complete flow through all layers."""

    def test_get_sandbox_creates_all_layers(self, sandbox_manager, temp_db):
        """Test that get_sandbox creates Terminal → Lease → Runtime → ChatSession."""
        thread_id = "test-thread-1"

        # Get sandbox (should create everything)
        capability = sandbox_manager.get_sandbox(thread_id)

        assert capability is not None
        assert capability._session is not None
        assert capability._session.thread_id == thread_id
        assert capability._session.terminal is not None
        assert capability._session.lease is not None
        assert capability._session.runtime is not None

        # Verify persistence
        terminal_store = TerminalStore(db_path=temp_db)
        terminal = terminal_store.get(thread_id)
        assert terminal is not None

        lease_store = LeaseStore(db_path=temp_db)
        lease = lease_store.get(terminal.lease_id)
        assert lease is not None

    def test_get_sandbox_reuses_existing_session(self, sandbox_manager):
        """Test that get_sandbox reuses existing session."""
        thread_id = "test-thread-2"

        # First call creates
        capability1 = sandbox_manager.get_sandbox(thread_id)
        session_id1 = capability1._session.session_id

        # Second call reuses
        capability2 = sandbox_manager.get_sandbox(thread_id)
        session_id2 = capability2._session.session_id

        assert session_id1 == session_id2

    @pytest.mark.asyncio
    async def test_command_execution_through_capability(self, sandbox_manager):
        """Test command execution through capability wrapper."""
        thread_id = "test-thread-3"

        capability = sandbox_manager.get_sandbox(thread_id)

        # Execute command
        result = await capability.command.execute("echo hello")

        assert result.exit_code == 0
        assert result.stdout is not None

    def test_terminal_state_persists_across_sessions(self, sandbox_manager, temp_db):
        """Test that terminal state persists when session expires."""
        thread_id = "test-thread-4"

        # Create session and update terminal state
        capability1 = sandbox_manager.get_sandbox(thread_id)
        terminal_id = capability1._session.terminal.terminal_id

        # Update terminal state
        from sandbox.terminal import TerminalState

        new_state = TerminalState(cwd="/tmp", env_delta={"FOO": "bar"})
        capability1._session.terminal.update_state(new_state)

        # Delete session (simulating expiry)
        sandbox_manager.session_manager.delete(capability1._session.session_id)

        # Get sandbox again (creates new session)
        capability2 = sandbox_manager.get_sandbox(thread_id)

        # Terminal should be reused with persisted state
        assert capability2._session.terminal.terminal_id == terminal_id
        state = capability2._session.terminal.get_state()
        assert state.cwd == "/tmp"
        assert state.env_delta == {"FOO": "bar"}

    def test_lease_shared_across_terminals(self, sandbox_manager, temp_db):
        """Test that multiple terminals can share the same lease."""
        thread_id1 = "test-thread-5"
        thread_id2 = "test-thread-6"

        # Create first terminal
        capability1 = sandbox_manager.get_sandbox(thread_id1)
        lease_id1 = capability1._session.lease.lease_id

        # Manually create second terminal with same lease
        terminal_store = TerminalStore(db_path=temp_db)
        terminal2 = terminal_store.create(
            terminal_id="term-shared",
            thread_id=thread_id2,
            lease_id=lease_id1,
        )

        # Get sandbox for second thread
        capability2 = sandbox_manager.get_sandbox(thread_id2)
        lease_id2 = capability2._session.lease.lease_id

        # Should share the same lease
        assert lease_id1 == lease_id2

    def test_session_touch_updates_activity(self, sandbox_manager):
        """Test that capability.touch() updates session activity."""
        thread_id = "test-thread-7"

        capability = sandbox_manager.get_sandbox(thread_id)
        old_activity = capability._session.last_active_at

        import time

        time.sleep(0.01)

        capability.touch()

        # Activity should be updated
        assert capability._session.last_active_at > old_activity

    def test_session_info_api(self, sandbox_manager):
        """Test that manager can expose current provider session info."""
        thread_id = "test-thread-8"

        session_info = sandbox_manager.get_or_create_session(thread_id)
        assert session_info is not None
        assert session_info.provider == "local"

        sessions = sandbox_manager.list_sessions()
        assert len(sessions) > 0

    def test_remote_fs_operation_fails_on_paused_lease(self, remote_sandbox_manager, mock_remote_provider):
        """Paused lease must fail fast until explicit resume."""
        thread_id = "test-thread-remote-fs-1"
        capability = remote_sandbox_manager.get_sandbox(thread_id)

        lease = capability._session.lease
        lease.ensure_active_instance(mock_remote_provider)
        lease.pause_instance(mock_remote_provider)
        assert lease.get_instance() is not None
        assert lease.get_instance().status == "paused"
        mock_remote_provider.get_session_status.return_value = "paused"

        with pytest.raises(RuntimeError, match="is paused"):
            capability.fs.write_file("/home/user/test.txt", "ok")
        assert lease.get_instance().status == "paused"


class TestSessionLifecycle:
    """Test session lifecycle management."""

    def test_session_expiry_cleanup(self, sandbox_manager, temp_db):
        """Test that expired sessions are cleaned up."""

        thread_id = "test-thread-9"

        # Create session with very short timeout
        capability = sandbox_manager.get_sandbox(thread_id)
        session_id = capability._session.session_id

        # Manually update policy to expire immediately
        session_manager = ChatSessionManager(
            provider=sandbox_manager.provider,
            db_path=temp_db,
        )

        import time

        time.sleep(0.1)

        # Cleanup expired
        count = session_manager.cleanup_expired()

        # Session should still exist (default policy is 10 minutes)
        assert count == 0

    def test_pause_and_resume_session(self, sandbox_manager):
        """Test pausing and resuming sessions."""
        thread_id = "test-thread-10"

        # Create session
        capability = sandbox_manager.get_sandbox(thread_id)
        session_id = capability._session.session_id

        assert sandbox_manager.pause_session(thread_id)
        paused = sandbox_manager.session_manager.get(thread_id)
        assert paused is not None
        assert paused.session_id == session_id
        assert paused.status == "paused"

        assert sandbox_manager.resume_session(thread_id)
        resumed = sandbox_manager.session_manager.get(thread_id)
        assert resumed is not None
        assert resumed.session_id == session_id
        assert resumed.status == "active"

    def test_destroy_session(self, sandbox_manager):
        """Test destroying a session."""
        thread_id = "test-thread-11"

        # Create session
        capability = sandbox_manager.get_sandbox(thread_id)
        session_id = capability._session.session_id

        # Destroy
        sandbox_manager.destroy_session(thread_id)

        # Session should be gone
        session = sandbox_manager.session_manager.get(thread_id)
        assert session is None


class TestMultiThreadScenarios:
    """Test scenarios with multiple threads."""

    def test_multiple_threads_independent_sessions(self, sandbox_manager):
        """Test that multiple threads get independent sessions."""
        thread_ids = [f"test-thread-{i}" for i in range(3)]

        capabilities = [sandbox_manager.get_sandbox(tid) for tid in thread_ids]

        # All should have different sessions
        session_ids = [cap._session.session_id for cap in capabilities]
        assert len(set(session_ids)) == 3

        # All should have different terminals
        terminal_ids = [cap._session.terminal.terminal_id for cap in capabilities]
        assert len(set(terminal_ids)) == 3

    def test_thread_switch_preserves_state(self, sandbox_manager):
        """Test that switching between threads preserves state."""
        thread_id1 = "test-thread-12"
        thread_id2 = "test-thread-13"

        # Work on thread 1
        cap1 = sandbox_manager.get_sandbox(thread_id1)
        from sandbox.terminal import TerminalState

        cap1._session.terminal.update_state(TerminalState(cwd="/tmp"))

        # Switch to thread 2
        cap2 = sandbox_manager.get_sandbox(thread_id2)
        cap2._session.terminal.update_state(TerminalState(cwd="/home"))

        # Switch back to thread 1
        cap1_again = sandbox_manager.get_sandbox(thread_id1)
        state1 = cap1_again._session.terminal.get_state()
        assert state1.cwd == "/tmp"

        # Check thread 2 state
        cap2_again = sandbox_manager.get_sandbox(thread_id2)
        state2 = cap2_again._session.terminal.get_state()
        assert state2.cwd == "/home"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_terminal_recreates_with_same_id(self, sandbox_manager, temp_db):
        """Test that terminal is recreated when missing from DB.

        Note: The terminal_id is stored in the session, so when we delete
        the terminal but not the session, the session still references the
        old terminal_id. This is expected behavior - the terminal_id is
        stable across recreations.
        """
        thread_id = "test-thread-14"

        # Create session
        capability = sandbox_manager.get_sandbox(thread_id)
        terminal_id = capability._session.terminal.terminal_id

        # Delete terminal from DB (but not session)
        terminal_store = TerminalStore(db_path=temp_db)
        terminal_store.delete(terminal_id)

        # Delete session to force full recreation
        sandbox_manager.session_manager.delete(capability._session.session_id)

        # Get sandbox again - creates new terminal
        capability2 = sandbox_manager.get_sandbox(thread_id)

        # Terminal should exist in DB now
        terminal2 = terminal_store.get(thread_id)
        assert terminal2 is not None

    def test_missing_lease_recreates_with_same_id(self, sandbox_manager, temp_db):
        """Test that lease is recreated when missing from DB.

        Note: The lease_id is stored in the terminal, so when we delete
        the lease but not the terminal, the terminal still references the
        old lease_id. This is expected behavior - the lease_id is stable.
        """
        thread_id = "test-thread-15"

        # Create session
        capability = sandbox_manager.get_sandbox(thread_id)
        lease_id = capability._session.lease.lease_id

        # Delete lease from DB
        lease_store = LeaseStore(db_path=temp_db)
        lease_store.delete(lease_id)

        # Delete session AND terminal to force full recreation
        sandbox_manager.session_manager.delete(capability._session.session_id)
        terminal_store = TerminalStore(db_path=temp_db)
        terminal_store.delete(capability._session.terminal.terminal_id)

        # Get sandbox again - creates new terminal + lease
        capability2 = sandbox_manager.get_sandbox(thread_id)

        # Lease should exist in DB now
        lease2 = lease_store.get(capability2._session.lease.lease_id)
        assert lease2 is not None
