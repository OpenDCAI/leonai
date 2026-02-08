"""
End-to-end tests with real sandbox providers.

Tests terminal persistence architecture through the agent interface.
Simulates all frontend interactions programmatically.
"""

import os
import pytest
import tempfile
from pathlib import Path

from agent import create_leon_agent
from sandbox.thread_context import set_current_thread_id


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_e2e.db"
    return str(db_path)


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return str(workspace)


class TestAgentBayE2E:
    """End-to-end tests with AgentBay provider."""

    @pytest.mark.skipif(
        not os.getenv("AGENTBAY_API_KEY"),
        reason="AGENTBAY_API_KEY not set"
    )
    def test_agentbay_basic_execution(self, test_db_path):
        """Test basic command execution through agent with AgentBay."""
        thread_id = "test-agentbay-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="agentbay",
            db_path=test_db_path
        )

        # Execute command through agent
        result = agent.sandbox.shell().execute("echo 'AgentBay Test'")
        assert result.exit_code == 0
        assert "AgentBay Test" in result.stdout

        agent.close()

    @pytest.mark.skipif(
        not os.getenv("AGENTBAY_API_KEY"),
        reason="AGENTBAY_API_KEY not set"
    )
    def test_agentbay_terminal_state_persistence(self, test_db_path):
        """Test terminal state persists across commands with AgentBay."""
        thread_id = "test-agentbay-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="agentbay",
            db_path=test_db_path
        )

        # Change directory
        agent.sandbox.shell().execute("cd /tmp")
        result = agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set environment variable
        agent.sandbox.shell().execute("export AGENTBAY_VAR=test123")
        result = agent.sandbox.shell().execute("echo $AGENTBAY_VAR")
        assert "test123" in result.stdout

        agent.close()

    @pytest.mark.skipif(
        not os.getenv("AGENTBAY_API_KEY"),
        reason="AGENTBAY_API_KEY not set"
    )
    def test_agentbay_file_operations(self, test_db_path):
        """Test file operations with AgentBay."""
        thread_id = "test-agentbay-files"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="agentbay",
            db_path=test_db_path
        )

        # Create file
        test_content = "AgentBay file test"
        agent.sandbox.shell().execute(f"echo '{test_content}' > /tmp/agentbay_test.txt")

        # Read file
        content = agent.sandbox.fs().read_file("/tmp/agentbay_test.txt")
        assert test_content in content

        # List directory
        files = agent.sandbox.fs().list_dir("/tmp")
        assert "agentbay_test.txt" in files

        agent.close()


@pytest.mark.skipif(
    not os.getenv("E2B_API_KEY"),
    reason="E2B_API_KEY not set"
)
class TestE2BE2E:
    """End-to-end tests with E2B provider."""

    def test_e2b_basic_execution(self, test_db_path):
        """Test basic command execution with E2B."""
        thread_id = "test-e2b-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="e2b",
            db_path=test_db_path
        )

        result = agent.sandbox.shell().execute("echo 'E2B Test'")
        assert result.exit_code == 0
        assert "E2B Test" in result.stdout

        agent.close()

    def test_e2b_terminal_state_persistence(self, test_db_path):
        """Test terminal state persistence with E2B."""
        thread_id = "test-e2b-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="e2b",
            db_path=test_db_path
        )

        # Change directory
        agent.sandbox.shell().execute("cd /tmp")
        result = agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set env var
        agent.sandbox.shell().execute("export E2B_VAR=test123")
        result = agent.sandbox.shell().execute("echo $E2B_VAR")
        assert "test123" in result.stdout

        agent.close()

    def test_e2b_file_operations(self, test_db_path):
        """Test file operations with E2B."""
        thread_id = "test-e2b-files"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="e2b",
            db_path=test_db_path
        )

        # Create file
        test_content = "E2B file test"
        agent.sandbox.shell().execute(f"echo '{test_content}' > /tmp/e2b_test.txt")

        # Read file
        content = agent.sandbox.fs().read_file("/tmp/e2b_test.txt")
        assert test_content in content

        agent.close()

    def test_e2b_pause_resume(self, test_db_path):
        """Test pause and resume with E2B."""
        thread_id = "test-e2b-pause"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="e2b",
            db_path=test_db_path
        )

        # Set state
        agent.sandbox.shell().execute("cd /tmp")
        agent.sandbox.shell().execute("export PAUSE_VAR=preserved")

        # Pause session
        agent.sandbox.manager.pause_session(thread_id)

        # Resume by getting sandbox again
        result = agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        result = agent.sandbox.shell().execute("echo $PAUSE_VAR")
        assert "preserved" in result.stdout

        agent.close()


@pytest.mark.skipif(
    not os.getenv("DAYTONA_API_KEY"),
    reason="DAYTONA_API_KEY not set"
)
class TestDaytonaE2E:
    """End-to-end tests with Daytona provider."""

    def test_daytona_basic_execution(self, test_db_path):
        """Test basic command execution with Daytona."""
        thread_id = "test-daytona-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="daytona",
            db_path=test_db_path
        )

        result = agent.sandbox.shell().execute("echo 'Daytona Test'")
        assert result.exit_code == 0
        assert "Daytona Test" in result.stdout

        agent.close()

    def test_daytona_terminal_state_persistence(self, test_db_path):
        """Test terminal state persistence with Daytona."""
        thread_id = "test-daytona-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(
            sandbox="daytona",
            db_path=test_db_path
        )

        # Change directory
        agent.sandbox.shell().execute("cd /tmp")
        result = agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set env var
        agent.sandbox.shell().execute("export DAYTONA_VAR=test456")
        result = agent.sandbox.shell().execute("echo $DAYTONA_VAR")
        assert "test456" in result.stdout

        agent.close()


class TestWebAPISimulation:
    """Simulate web API interactions programmatically."""

    def test_simulate_session_status_endpoints(self, test_db_path):
        """Simulate: GET /api/threads/{id}/session, /terminal, /lease"""
        from sandbox.manager import SandboxManager
        from sandbox.sqlite_store import SQLiteSessionStore
        from sandbox.provider import SandboxProvider

        # Create a mock provider
        class MockProvider(SandboxProvider):
            name = "MockProvider"

            def create_session(self, context_id: str | None = None):
                from sandbox.provider import SessionInfo
                return SessionInfo(
                    session_id=f"mock-{context_id or 'default'}",
                    provider="MockProvider",
                    status="running",
                    metadata={}
                )

            def destroy_session(self, session_id: str, sync: bool = True) -> bool:
                return True

            def pause_session(self, session_id: str) -> bool:
                return True

            def resume_session(self, session_id: str) -> bool:
                return True

            def get_session_status(self, session_id: str) -> str:
                return "running"

            def execute(self, session_id: str, command: str, timeout_ms: int = 30000, cwd: str | None = None):
                from sandbox.provider import ProviderExecResult
                return ProviderExecResult(
                    output="mock output",
                    exit_code=0,
                    error=None
                )

            def read_file(self, session_id: str, path: str) -> str:
                return "mock file content"

            def write_file(self, session_id: str, path: str, content: str) -> str:
                return path

            def list_dir(self, session_id: str, path: str) -> list[dict]:
                return [
                    {"name": "file1.txt", "type": "file"},
                    {"name": "file2.txt", "type": "file"}
                ]

            def get_metrics(self, session_id: str):
                from sandbox.provider import Metrics
                return Metrics(
                    cpu_percent=10.0,
                    memory_used_mb=100.0,
                    memory_total_mb=1024.0,
                    disk_used_gb=1.0,
                    disk_total_gb=10.0,
                    network_rx_kbps=0.0,
                    network_tx_kbps=0.0
                )

        provider = MockProvider()
        store = SQLiteSessionStore(test_db_path)
        manager = SandboxManager(provider=provider, store=store, db_path=test_db_path)

        thread_id = "test-status-thread"

        # Simulate GET /api/threads/{id}/session
        sandbox = manager.get_sandbox(thread_id)

        # Trigger instance creation by accessing the runtime
        session = manager.session_manager.get(thread_id)
        from sandbox.runtime import RemoteWrappedRuntime
        if isinstance(session.runtime, RemoteWrappedRuntime):
            session.lease.ensure_active_instance(session.runtime.provider)

        assert session is not None
        assert session.thread_id == thread_id
        assert not session.is_expired()

        # Simulate GET /api/threads/{id}/terminal
        terminal = manager.terminal_store.get(thread_id)
        assert terminal is not None
        state = terminal.get_state()
        assert state.cwd is not None
        assert state.state_version >= 0

        # Simulate GET /api/threads/{id}/lease
        lease = manager.lease_store.get(terminal.lease_id)
        assert lease is not None
        assert lease.provider_name == "MockProvider"
        instance = lease.get_instance()
        assert instance is not None
        assert instance.status == "running"

        manager.destroy_session(thread_id)

    def test_simulate_pause_resume_flow(self, test_db_path):
        """Simulate: POST /api/threads/{id}/pause + POST /api/threads/{id}/resume"""
        import asyncio
        from sandbox.manager import SandboxManager
        from sandbox.sqlite_store import SQLiteSessionStore
        from sandbox.provider import SandboxProvider

        class MockProvider(SandboxProvider):
            name = "MockProvider"

            def __init__(self):
                self.paused = False

            def create_session(self, context_id: str | None = None):
                from sandbox.provider import SessionInfo
                return SessionInfo(
                    session_id=f"mock-{context_id or 'default'}",
                    provider="MockProvider",
                    status="running",
                    metadata={}
                )

            def destroy_session(self, session_id: str, sync: bool = True) -> bool:
                return True

            def pause_session(self, session_id: str) -> bool:
                self.paused = True
                return True

            def resume_session(self, session_id: str) -> bool:
                self.paused = False
                return True

            def get_session_status(self, session_id: str) -> str:
                return "paused" if self.paused else "running"

            def execute(self, session_id: str, command: str, timeout_ms: int = 30000, cwd: str | None = None):
                from sandbox.provider import ProviderExecResult
                return ProviderExecResult(
                    output="output",
                    exit_code=0,
                    error=None
                )

            def read_file(self, session_id: str, path: str) -> str:
                return "content"

            def write_file(self, session_id: str, path: str, content: str) -> str:
                return path

            def list_dir(self, session_id: str, path: str) -> list[dict]:
                return []

            def get_metrics(self, session_id: str):
                from sandbox.provider import Metrics
                return Metrics(
                    cpu_percent=10.0,
                    memory_used_mb=100.0,
                    memory_total_mb=1024.0,
                    disk_used_gb=1.0,
                    disk_total_gb=10.0,
                    network_rx_kbps=0.0,
                    network_tx_kbps=0.0
                )

        async def run_test():
            provider = MockProvider()
            store = SQLiteSessionStore(test_db_path)
            manager = SandboxManager(provider=provider, store=store, db_path=test_db_path)

            thread_id = "test-pause-thread"

            # Create session
            sandbox = manager.get_sandbox(thread_id)
            result = await sandbox.command.execute("echo test")
            assert result.exit_code == 0

            # Simulate POST /api/threads/{id}/pause
            manager.pause_session(thread_id)
            assert provider.paused

            # Simulate POST /api/threads/{id}/resume
            manager.resume_session(thread_id)
            assert not provider.paused

            manager.destroy_session(thread_id)

        asyncio.run(run_test())

    def test_simulate_multiple_threads(self, test_db_path):
        """Simulate multiple threads with independent state."""
        import asyncio
        from sandbox.manager import SandboxManager
        from sandbox.sqlite_store import SQLiteSessionStore
        from sandbox.provider import SandboxProvider

        class MockProvider(SandboxProvider):
            name = "MockProvider"

            def create_session(self, context_id: str | None = None):
                from sandbox.provider import SessionInfo
                return SessionInfo(
                    session_id=f"mock-{context_id or 'default'}",
                    provider="MockProvider",
                    status="running",
                    metadata={}
                )

            def destroy_session(self, session_id: str, sync: bool = True) -> bool:
                return True

            def pause_session(self, session_id: str) -> bool:
                return True

            def resume_session(self, session_id: str) -> bool:
                return True

            def get_session_status(self, session_id: str) -> str:
                return "running"

            def execute(self, session_id: str, command: str, timeout_ms: int = 30000, cwd: str | None = None):
                from sandbox.provider import ProviderExecResult
                return ProviderExecResult(
                    output=f"output from {cwd}",
                    exit_code=0,
                    error=None
                )

            def read_file(self, session_id: str, path: str) -> str:
                return "content"

            def write_file(self, session_id: str, path: str, content: str) -> str:
                return path

            def list_dir(self, session_id: str, path: str) -> list[dict]:
                return []

            def get_metrics(self, session_id: str):
                from sandbox.provider import Metrics
                return Metrics(
                    cpu_percent=10.0,
                    memory_used_mb=100.0,
                    memory_total_mb=1024.0,
                    disk_used_gb=1.0,
                    disk_total_gb=10.0,
                    network_rx_kbps=0.0,
                    network_tx_kbps=0.0
                )

        async def run_test():
            provider = MockProvider()
            store = SQLiteSessionStore(test_db_path)
            manager = SandboxManager(provider=provider, store=store, db_path=test_db_path)

            # Create two threads
            thread1 = "test-multi-1"
            thread2 = "test-multi-2"

            sandbox1 = manager.get_sandbox(thread1)
            sandbox2 = manager.get_sandbox(thread2)

            # Execute commands
            result1 = await sandbox1.command.execute("echo test1")
            result2 = await sandbox2.command.execute("echo test2")

            assert result1.exit_code == 0
            assert result2.exit_code == 0

            # Verify independent sessions
            session1 = manager.session_manager.get(thread1)
            session2 = manager.session_manager.get(thread2)

            assert session1.thread_id == thread1
            assert session2.thread_id == thread2
            assert session1.session_id != session2.session_id

            # Verify independent terminals
            terminal1 = manager.terminal_store.get(thread1)
            terminal2 = manager.terminal_store.get(thread2)

            assert terminal1.terminal_id != terminal2.terminal_id

            manager.destroy_session(thread1)
            manager.destroy_session(thread2)

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
