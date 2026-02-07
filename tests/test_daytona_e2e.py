"""End-to-end tests for Daytona sandbox."""

import os
import tempfile
from pathlib import Path

import pytest

from sandbox import DaytonaSandbox, SandboxConfig

pytestmark = pytest.mark.skipif(
    not os.getenv("DAYTONA_API_KEY"),
    reason="DAYTONA_API_KEY not set",
)


@pytest.fixture
def daytona_sandbox():
    """Create a Daytona sandbox for testing."""
    config = SandboxConfig(
        provider="daytona",
        on_exit="destroy",
    )
    config.daytona.api_key = os.getenv("DAYTONA_API_KEY")
    config.daytona.api_url = os.getenv("DAYTONA_API_URL", "https://app.daytona.io/api")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        sandbox = DaytonaSandbox(config, db_path=db_path)
        yield sandbox
        sandbox.close()


class TestDaytonaSandboxE2E:
    """End-to-end tests for Daytona sandbox."""

    def test_file_operations(self, daytona_sandbox):
        """Test file read/write/list operations."""
        from sandbox.thread_context import set_current_thread_id

        thread_id = "test-daytona-files"
        set_current_thread_id(thread_id)

        daytona_sandbox.ensure_session(thread_id)

        fs = daytona_sandbox.fs()
        assert fs is not None

        test_path = "/workspace/test.txt"
        result = fs.write_file(test_path, "Hello Daytona")
        assert result.success

        read_result = fs.read_file(test_path)
        assert read_result.content == "Hello Daytona"

        list_result = fs.list_dir("/workspace")
        assert not list_result.error
        assert any(e.name == "test.txt" for e in list_result.entries)

    def test_command_execution(self, daytona_sandbox):
        """Test command execution."""
        import asyncio

        from sandbox.thread_context import set_current_thread_id

        thread_id = "test-daytona-cmd"
        set_current_thread_id(thread_id)

        daytona_sandbox.ensure_session(thread_id)

        shell = daytona_sandbox.shell()
        assert shell is not None

        result = asyncio.run(shell.execute("echo 'test command'"))
        assert result.success
        assert "test command" in result.stdout

        result = asyncio.run(shell.execute("pwd"))
        assert result.success
        assert "/workspace" in result.stdout
