"""Sandbox interfaces — ABC + data classes for executor and filesystem.

Re-exports everything from executor and filesystem submodules.
"""

from sandbox.interfaces.executor import (
    AsyncCommand,
    BaseExecutor,
    ExecuteResult,
)
from sandbox.interfaces.filesystem import (
    DirEntry,
    DirListResult,
    FileReadResult,
    FileSystemBackend,
    FileWriteResult,
)

__all__ = [
    # Executor
    "BaseExecutor",
    "ExecuteResult",
    "AsyncCommand",
    # Filesystem
    "FileSystemBackend",
    "FileReadResult",
    "FileWriteResult",
    "DirEntry",
    "DirListResult",
]
