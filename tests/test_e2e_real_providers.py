"""
Real end-to-end tests with actual sandbox providers.

NO MOCKS - Tests real command execution, terminal state persistence,
and file operations through the actual agent interface.
"""

import os

import pytest

from agent import create_leon_agent
from sandbox.thread_context import set_current_thread_id


@pytest.mark.skipif(not os.getenv("E2B_API_KEY"), reason="E2B_API_KEY not set")
class TestE2BRealE2E:
    """Real E2E tests with E2B provider - NO MOCKS."""

    @pytest.mark.asyncio
    async def test_e2b_basic_execution(self):
        """Test basic command execution with real E2B sandbox."""
        thread_id = "test-e2b-real-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="e2b")

        # Execute real command
        result = await agent.sandbox.shell().execute("echo 'E2B Real Test'")
        assert result.exit_code == 0
        assert "E2B Real Test" in result.stdout

        agent.close()

    @pytest.mark.asyncio
    async def test_e2b_terminal_state_persistence(self):
        """Test terminal state persists across real commands."""
        thread_id = "test-e2b-real-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="e2b")

        # Change directory
        await agent.sandbox.shell().execute("cd /tmp")
        result = await agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set environment variable
        await agent.sandbox.shell().execute("export E2B_TEST_VAR=real123")
        result = await agent.sandbox.shell().execute("echo $E2B_TEST_VAR")
        assert "real123" in result.stdout

        agent.close()

    @pytest.mark.asyncio
    async def test_e2b_file_operations(self):
        """Test file operations with real E2B sandbox."""
        thread_id = "test-e2b-real-files"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="e2b")

        # Create file
        test_content = "E2B real file test"
        await agent.sandbox.shell().execute(f"echo '{test_content}' > /tmp/e2b_real_test.txt")

        # Read file
        content = await agent.sandbox.fs().read_file("/tmp/e2b_real_test.txt")
        assert test_content in content

        # List directory
        files = await agent.sandbox.fs().list_dir("/tmp")
        assert any("e2b_real_test.txt" in str(f) for f in files)

        agent.close()

    @pytest.mark.asyncio
    async def test_e2b_multiple_commands_state_tracking(self):
        """Test state tracking across multiple real commands."""
        thread_id = "test-e2b-real-multi"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="e2b")

        # Execute multiple commands and verify state persists
        await agent.sandbox.shell().execute("cd /home")
        await agent.sandbox.shell().execute("export VAR1=value1")
        await agent.sandbox.shell().execute("export VAR2=value2")

        result = await agent.sandbox.shell().execute("pwd && echo $VAR1 && echo $VAR2")
        assert "/home" in result.stdout
        assert "value1" in result.stdout
        assert "value2" in result.stdout

        agent.close()


@pytest.mark.skipif(not os.getenv("AGENTBAY_API_KEY"), reason="AGENTBAY_API_KEY not set")
class TestAgentBayRealE2E:
    """Real E2E tests with AgentBay provider - NO MOCKS."""

    @pytest.mark.asyncio
    async def test_agentbay_basic_execution(self):
        """Test basic command execution with real AgentBay sandbox."""
        thread_id = "test-agentbay-real-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="agentbay")

        # Execute real command
        result = await agent.sandbox.shell().execute("echo 'AgentBay Real Test'")
        assert result.exit_code == 0
        assert "AgentBay Real Test" in result.stdout

        agent.close()

    @pytest.mark.asyncio
    async def test_agentbay_terminal_state_persistence(self):
        """Test terminal state persists across real commands."""
        thread_id = "test-agentbay-real-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="agentbay")

        # Change directory
        await agent.sandbox.shell().execute("cd /tmp")
        result = await agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set environment variable
        await agent.sandbox.shell().execute("export AGENTBAY_TEST_VAR=real456")
        result = await agent.sandbox.shell().execute("echo $AGENTBAY_TEST_VAR")
        assert "real456" in result.stdout

        agent.close()

    @pytest.mark.asyncio
    async def test_agentbay_file_operations(self):
        """Test file operations with real AgentBay sandbox."""
        thread_id = "test-agentbay-real-files"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="agentbay")

        # Create file
        test_content = "AgentBay real file test"
        await agent.sandbox.shell().execute(f"echo '{test_content}' > /tmp/agentbay_real_test.txt")

        # Read file
        content = await agent.sandbox.fs().read_file("/tmp/agentbay_real_test.txt")
        assert test_content in content

        agent.close()


@pytest.mark.skipif(not os.getenv("DAYTONA_API_KEY"), reason="DAYTONA_API_KEY not set")
class TestDaytonaRealE2E:
    """Real E2E tests with Daytona provider - NO MOCKS."""

    @pytest.mark.asyncio
    async def test_daytona_basic_execution(self):
        """Test basic command execution with real Daytona sandbox."""
        thread_id = "test-daytona-real-basic"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="daytona")

        # Execute real command
        result = await agent.sandbox.shell().execute("echo 'Daytona Real Test'")
        assert result.exit_code == 0
        assert "Daytona Real Test" in result.stdout

        agent.close()

    @pytest.mark.asyncio
    async def test_daytona_terminal_state_persistence(self):
        """Test terminal state persists across real commands."""
        thread_id = "test-daytona-real-state"
        set_current_thread_id(thread_id)

        agent = create_leon_agent(sandbox="daytona")

        # Change directory
        await agent.sandbox.shell().execute("cd /tmp")
        result = await agent.sandbox.shell().execute("pwd")
        assert "/tmp" in result.stdout

        # Set environment variable
        await agent.sandbox.shell().execute("export DAYTONA_TEST_VAR=real789")
        result = await agent.sandbox.shell().execute("echo $DAYTONA_TEST_VAR")
        assert "real789" in result.stdout

        agent.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
