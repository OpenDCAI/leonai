"""Command execution middleware with extensible hook system.

Custom implementation with run_command and command_status tools.
"""

from .hooks import CommandHook, HookResult, load_hooks
from .middleware import CommandMiddleware

__all__ = ["CommandMiddleware", "CommandHook", "HookResult", "load_hooks"]
