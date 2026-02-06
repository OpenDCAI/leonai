"""Sandbox — infrastructure layer for execution environments.

Usage:
    from sandbox import create_sandbox, Sandbox, SandboxConfig

    config = SandboxConfig.load("agentbay")
    sbx = create_sandbox(config, db_path=db_path)

    FileSystemMiddleware(backend=sbx.fs())
    CommandMiddleware(executor=sbx.shell())
"""

from __future__ import annotations

from pathlib import Path

from sandbox.base import Sandbox
from sandbox.config import SandboxConfig, resolve_sandbox_name
from sandbox.thread_context import get_current_thread_id, set_current_thread_id


def create_sandbox(
    config: SandboxConfig,
    workspace_root: str | None = None,
    db_path: Path | None = None,
) -> Sandbox:
    """Factory: create a Sandbox from config.

    Args:
        config: SandboxConfig (from SandboxConfig.load() or inline)
        workspace_root: Fallback working dir for LocalSandbox
        db_path: SQLite path for session tracking
    """
    provider = config.provider

    if provider == "local":
        from sandbox.local import LocalSandbox

        return LocalSandbox(workspace_root=workspace_root or str(Path.cwd()))

    if provider == "agentbay":
        from sandbox.agentbay import AgentBaySandbox

        return AgentBaySandbox(config=config, db_path=db_path)

    if provider == "docker":
        from sandbox.docker import DockerSandbox

        return DockerSandbox(config=config, db_path=db_path)

    if provider == "e2b":
        from sandbox.e2b import E2BSandbox

        return E2BSandbox(config=config, db_path=db_path)

    raise ValueError(f"Unknown sandbox provider: {provider}")


__all__ = [
    "Sandbox",
    "SandboxConfig",
    "create_sandbox",
    "resolve_sandbox_name",
    "set_current_thread_id",
    "get_current_thread_id",
]
