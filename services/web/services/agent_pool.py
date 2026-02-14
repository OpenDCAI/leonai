"""Agent pool management service."""

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from agent import create_leon_agent
from sandbox.manager import lookup_sandbox_for_thread
from sandbox.thread_context import set_current_thread_id


def create_agent_sync(sandbox_name: str, workspace_root: Path | None = None) -> Any:
    """Create a LeonAgent with the given sandbox. Runs in a thread."""
    # @@@ model_name=None lets the profile.yaml value take effect instead of the factory default
    return create_leon_agent(
        model_name=None,
        workspace_root=workspace_root or Path.cwd(),
        sandbox=sandbox_name if sandbox_name != "local" else None,
        verbose=True,
    )


async def get_or_create_agent(app_obj: FastAPI, sandbox_type: str, thread_id: str | None = None) -> Any:
    """Lazy agent pool — one agent per thread, created on demand."""
    if thread_id:
        set_current_thread_id(thread_id)

    # Per-thread Agent instance: pool key = thread_id:sandbox_type
    # This ensures complete isolation of middleware state (memory, todo, runtime, filesystem, etc.)
    if not thread_id:
        raise ValueError("thread_id is required for agent creation")

    pool_key = f"{thread_id}:{sandbox_type}"
    pool = app_obj.state.agent_pool
    if pool_key in pool:
        return pool[pool_key]

    # For local sandbox, check if thread has custom cwd
    workspace_root = None
    if sandbox_type == "local":
        cwd = app_obj.state.thread_cwd.get(thread_id)
        if cwd:
            workspace_root = Path(cwd).resolve()

    # @@@ agent-init-thread - LeonAgent.__init__ uses run_until_complete, must run in thread
    agent = await asyncio.to_thread(create_agent_sync, sandbox_type, workspace_root)
    pool[pool_key] = agent
    return agent


def resolve_thread_sandbox(app_obj: FastAPI, thread_id: str) -> str:
    """Look up sandbox type for a thread: memory cache → SQLite → default 'local'."""
    mapping = app_obj.state.thread_sandbox
    if thread_id in mapping:
        return mapping[thread_id]
    detected = lookup_sandbox_for_thread(thread_id)
    if detected:
        mapping[thread_id] = detected
        return detected
    return "local"
