"""Tests for CommandMiddleware."""

import asyncio
import pytest

from middleware.command import CommandMiddleware
from middleware.command.base import ExecuteResult
from middleware.command.dispatcher import get_executor, get_shell_info
from middleware.shell.hooks.dangerous_commands import DangerousCommandsHook


class TestExecuteResult:
    def test_success(self):
        result = ExecuteResult(exit_code=0, stdout="hello", stderr="")
        assert result.success
        assert result.output == "hello"
        assert result.to_tool_result() == "hello"

    def test_failure(self):
        result = ExecuteResult(exit_code=1, stdout="", stderr="error")
        assert not result.success
        assert "error" in result.output
        assert "Exit code: 1" in result.to_tool_result()

    def test_timeout(self):
        result = ExecuteResult(exit_code=-1, stdout="", stderr="", timed_out=True)
        assert not result.success
        assert "timed out" in result.to_tool_result().lower()


class TestDispatcher:
    def test_get_executor(self):
        executor = get_executor()
        assert executor is not None
        assert executor.shell_name in ("zsh", "bash", "powershell")

    def test_get_shell_info(self):
        info = get_shell_info()
        assert "os" in info
        assert "shell_name" in info
        assert "shell_path" in info


class TestExecutor:
    @pytest.mark.asyncio
    async def test_execute_echo(self):
        executor = get_executor()
        result = await executor.execute("echo hello")
        assert result.success
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_execute_with_cwd(self, tmp_path):
        executor = get_executor()
        result = await executor.execute("pwd", cwd=str(tmp_path))
        assert result.success
        assert str(tmp_path) in result.stdout

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        executor = get_executor()
        result = await executor.execute("sleep 10", timeout=0.1)
        assert result.timed_out
        assert not result.success

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(self):
        executor = get_executor()
        result = await executor.execute("nonexistent_command_12345")
        assert not result.success
        assert result.exit_code != 0


class TestAsyncExecution:
    @pytest.mark.asyncio
    async def test_execute_async(self):
        executor = get_executor()
        async_cmd = await executor.execute_async("echo async_test")
        assert async_cmd.command_id is not None
        
        result = await executor.wait_for(async_cmd.command_id, timeout=5.0)
        assert result is not None
        assert result.success
        assert "async_test" in result.stdout

    @pytest.mark.asyncio
    async def test_get_status(self):
        executor = get_executor()
        async_cmd = await executor.execute_async("sleep 0.1 && echo done")
        
        status = await executor.get_status(async_cmd.command_id)
        assert status is not None
        
        await asyncio.sleep(0.2)
        
        status = await executor.get_status(async_cmd.command_id)
        assert status is not None
        assert status.done


class TestDangerousCommandsHook:
    def test_block_rm_rf(self):
        hook = DangerousCommandsHook()
        result = hook.check_command("rm -rf /", {})
        assert not result.allow
        assert "SECURITY" in result.error_message

    def test_block_sudo(self):
        hook = DangerousCommandsHook()
        result = hook.check_command("sudo apt install", {})
        assert not result.allow

    def test_allow_safe_command(self):
        hook = DangerousCommandsHook()
        result = hook.check_command("echo hello", {})
        assert result.allow

    def test_block_network_when_enabled(self):
        hook = DangerousCommandsHook(block_network=True)
        result = hook.check_command("curl https://example.com", {})
        assert not result.allow

    def test_allow_network_when_disabled(self):
        hook = DangerousCommandsHook(block_network=False)
        result = hook.check_command("curl https://example.com", {})
        assert result.allow


class TestCommandMiddleware:
    def test_init(self, tmp_path):
        middleware = CommandMiddleware(workspace_root=tmp_path)
        assert middleware.workspace_root == tmp_path
        assert len(middleware.tools) == 2

    def test_init_with_hooks(self, tmp_path):
        hooks = [DangerousCommandsHook()]
        middleware = CommandMiddleware(workspace_root=tmp_path, hooks=hooks)
        assert len(middleware.hooks) == 1

    def test_check_hooks_block(self, tmp_path):
        hooks = [DangerousCommandsHook()]
        middleware = CommandMiddleware(workspace_root=tmp_path, hooks=hooks)
        allowed, error = middleware._check_hooks("rm -rf /")
        assert not allowed
        assert "SECURITY" in error

    def test_check_hooks_allow(self, tmp_path):
        hooks = [DangerousCommandsHook()]
        middleware = CommandMiddleware(workspace_root=tmp_path, hooks=hooks)
        allowed, error = middleware._check_hooks("echo hello")
        assert allowed
        assert error == ""
