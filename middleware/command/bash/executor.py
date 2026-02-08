"""Bash executor implementation using asyncio subprocess."""

from __future__ import annotations

import asyncio
import os
import uuid

from ..base import AsyncCommand, BaseExecutor, ExecuteResult
from ..persistent_executor import PersistentExecutor

_RUNNING_COMMANDS: dict[str, AsyncCommand] = {}


class BashExecutor(PersistentExecutor):
    """Executor for bash shell (Linux default)."""

    shell_name = "bash"
    shell_command = ("/bin/bash", "-i")

    def __init__(self, default_cwd: str | None = None):
        super().__init__(
            shell_command=self.shell_command,
            shell_name=self.shell_name,
            default_cwd=default_cwd,
            startup_commands=["export PS1=''"],
        )

